"""prop_sim.py - prop-firm simulator. Volta's objective since 2026-10-20: maximise PAYOUTS minus evaluation fees.

Rule sets live in knowledge/prop_firms.json (any firm can be added there - Volta files a wish when it wants a new firm).
A strategy's real day-by-day results on NQ (points per MNQ after costs, from strategy_lab.backtest on 1-minute bars)
are run through complete accounts in historical order, starting on every possible day: evaluation -> funded -> payouts.
Modelled: profit target, max loss (end-of-day or intraday trailing, lock at start + X), evaluation consistency,
funded consistency, contract limits and funded scaling tiers, payout qualification (days, min daily profit, cycle
profit), payout fraction / caps / minimum / buffer, profit split, N payouts -> live (success), fee + activation.
The max loss is checked against each trade's worst point (stop-based trades: the stop).
Daily loss limit (optional "eval_dll" / "fund_dll" in a plan, $): the bot never risks more than the limit in one day, so
the contracts of a day are capped at floor(limit / that day's worst loss per contract) - a trade that does not fit is
skipped. An account that cannot trade even 1 contract on a trade day is dead ("stuck": in the farm its slot is freed
and a new evaluation bought, instead of a zombie account that never pays and never costs). Copy-trading (farm): every account trades the same day's result, so losses land on the same days; the farm
reports the worst single day across all accounts."""
import json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
MNQ = 2.0
FIRMS_FILE = os.path.join(HERE, "knowledge", "prop_firms.json")


def plans():
    return {p["id"]: p for p in json.load(open(FIRMS_FILE))}


def _size(size_fn, phase, profit, buf, P):
    """Account playbooks may want the plan (e.g. to size toward the eval target); plain sizers get (phase, profit, buf)."""
    return size_fn(phase, profit, buf, P) if getattr(size_fn, "wants_plan", False) else size_fn(phase, profit, buf)


def _tier(tiers, profit):
    n = tiers[0][1]
    for lo, m in tiers:
        if profit >= lo: n = m
    return n


def _dll_cap(P, phase, n, worst):
    """Contracts allowed today under the plan's daily loss limit (if any): one day's worst case must fit inside it."""
    lim = P.get("eval_dll" if phase == "eval" else "fund_dll")
    if not lim or worst >= 0: return n
    return int(min(n, lim // (-worst * MNQ)))


def run_account(day_pts, day_worst, start, P, size_fn, max_days=400):
    S0 = float(P["size"]); bal = peak = S0; floor = S0 - P["mll"]; lock = S0 + P.get("lock_over_start", 100)
    phase = "eval"; days = 0; eval_days = []; payouts = []; cycle_days = []; cycle_start = bal
    for i in range(start, min(len(day_pts), start + max_days)):
        days += 1
        profit = bal - S0
        cap = P["eval_max_mnq"] if phase == "eval" else _tier(P["fund_max_tiers"], profit)
        n = _dll_cap(P, phase, int(min(cap, max(0, _size(size_fn, phase, profit, bal - floor, P)))), day_worst[i])
        if n == 0 and day_worst[i] < 0:                          # not even 1 contract fits (buffer or daily limit): dead
            return dict(passed=phase == "funded", payouts=payouts, days=days, end="stuck")
        pnl = n * day_pts[i] * MNQ; worst = n * day_worst[i] * MNQ
        if bal + worst <= floor:
            return dict(passed=phase == "funded", payouts=payouts, days=days, end="blown")
        if P.get("mll_type") == "intraday" and pnl > 0:          # intraday trailing: the day's best point raises the floor
            floor = max(floor, min(bal + pnl - P["mll"], lock))
        bal += pnl
        if phase == "eval":
            eval_days.append(pnl); tot = bal - S0
            if tot >= P["target"] and (P["eval_consistency"] is None or max(eval_days) <= P["eval_consistency"] * tot):
                phase = "funded"; bal = peak = S0; floor = S0 - P["mll"]; cycle_days = []; cycle_start = bal
                continue
        else:
            cycle_days.append(pnl); prof_cycle = bal - cycle_start; profit = bal - S0
            ok_days = sum(d >= max(P["day_min"], 0.01) for d in cycle_days)
            cons_ok = not P["fund_consistency"] or prof_cycle <= 0 or max(cycle_days) <= P["fund_consistency"] * prof_cycle
            if ok_days >= P["payout_days"] and prof_cycle > P["cycle_min"] and cons_ok and profit > 0:
                req = min(P["payout_frac"] * profit, P["caps"][min(len(payouts), len(P["caps"]) - 1)], bal - floor - P["buffer"])
                if req >= P["min_req"]:
                    bal -= req; payouts.append(P["split"] * req); cycle_days = []; cycle_start = bal
                    if len(payouts) >= P["payouts_to_live"]:
                        return dict(passed=True, payouts=payouts, days=days, end="live")
        peak = max(peak, bal)
        floor = max(floor, min(peak - P["mll"], lock))
    return dict(passed=phase == "funded", payouts=payouts, days=days, end="timeout")


def evaluate(day_pts, day_worst, plan="lucid_flex_25k", size_fn=None, starts=None, step=3):
    P = plans()[plan] if isinstance(plan, str) else plan
    size_fn = size_fn or (lambda phase, profit, buf: 2)
    starts = range(0, max(1, len(day_pts) - 60), step) if starts is None else starts
    R = [run_account(day_pts, day_worst, s, P, size_fn) for s in starts]
    pay = np.array([sum(r["payouts"]) for r in R]); cost = P["fee"] + P.get("activation", 0) * np.array([r["passed"] for r in R])
    return {"plan": P["id"], "accounts": len(R), "pass_rate": round(float(np.mean([r["passed"] for r in R])), 3),
            "avg_payout_per_eval": round(float(pay.mean()), 1), "ev_per_eval": round(float((pay - cost).mean()), 1),
            "share_with_payout": round(float((pay > 0).mean()), 3), "reach_live": round(float(np.mean([r["end"] == "live" for r in R])), 3),
            "median_days": int(np.median([r["days"] for r in R])), "fee": P["fee"]}


def best_plan(day_pts, day_worst, size_for, starts=None, step=4):
    """Score a strategy on every firm/plan; size_for(plan) -> size_fn. Returns all results, best first (by EV)."""
    out = [evaluate(day_pts, day_worst, P, size_for(P), starts, step) for P in plans().values()]
    return sorted(out, key=lambda r: -r["ev_per_eval"])


class Account:
    """One prop account, stepped day by day (same rules as run_account)."""
    def __init__(self, P):
        self.P = P; S0 = float(P["size"]); self.S0 = S0; self.bal = self.peak = S0; self.floor = S0 - P["mll"]
        self.lock = S0 + P.get("lock_over_start", 100); self.phase = "eval"; self.eval_days = []; self.payouts = []
        self.cycle_days = []; self.cycle_start = S0; self.end = None

    def step(self, pts, worst, size_fn):
        """Trade one day. Returns the payout paid to the trader today (0 if none). Sets self.end when finished."""
        P = self.P; profit = self.bal - self.S0
        cap = P["eval_max_mnq"] if self.phase == "eval" else _tier(P["fund_max_tiers"], profit)
        n = _dll_cap(P, self.phase, int(min(cap, max(0, _size(size_fn, self.phase, profit, self.bal - self.floor, P)))), worst)
        if n == 0 and worst < 0:                                   # can no longer trade a single contract: abandoned,
            self.end = "stuck"; self.last_pnl = 0.0; return 0.0    # the farm frees the slot and buys a new evaluation
        pnl = n * pts * MNQ; w = n * worst * MNQ; self.last_pnl = pnl
        if self.bal + w <= self.floor:
            self.end = "blown"; self.last_pnl = w; return 0.0
        if P.get("mll_type") == "intraday" and pnl > 0:
            self.floor = max(self.floor, min(self.bal + pnl - P["mll"], self.lock))
        self.bal += pnl; paid = 0.0
        if self.phase == "eval":
            self.eval_days.append(pnl); tot = self.bal - self.S0
            if tot >= P["target"] and (P["eval_consistency"] is None or max(self.eval_days) <= P["eval_consistency"] * tot):
                self.phase = "funded"; self.bal = self.peak = self.S0; self.floor = self.S0 - P["mll"]
                self.cycle_days = []; self.cycle_start = self.S0; self.passed_now = True
                return 0.0
        else:
            self.cycle_days.append(pnl); prof_cycle = self.bal - self.cycle_start; profit = self.bal - self.S0
            ok_days = sum(d >= max(P["day_min"], 0.01) for d in self.cycle_days)
            cons_ok = not P["fund_consistency"] or prof_cycle <= 0 or max(self.cycle_days) <= P["fund_consistency"] * prof_cycle
            if ok_days >= P["payout_days"] and prof_cycle > P["cycle_min"] and cons_ok and profit > 0:
                req = min(P["payout_frac"] * profit, P["caps"][min(len(self.payouts), len(P["caps"]) - 1)], self.bal - self.floor - P["buffer"])
                if req >= P["min_req"]:
                    self.bal -= req; paid = P["split"] * req; self.payouts.append(paid); self.cycle_days = []; self.cycle_start = self.bal
                    if len(self.payouts) >= P["payouts_to_live"]: self.end = "live"
        self.peak = max(self.peak, self.bal); self.floor = max(self.floor, min(self.peak - P["mll"], self.lock))
        return paid


def farm(day_pts, day_worst, dates, plan, size_fn, slots=5, budget_per_month=None):
    """Run a 'farm' of `slots` accounts on the same plan, all copy-trading the same strategy (same direction - no hedging).
    When an account blows up (or reaches live), a new evaluation is bought the next day. Accounts start staggered (one
    new per day at the beginning). Returns monthly cash flow: payouts received minus fees paid."""
    P = plans()[plan] if isinstance(plan, str) else plan
    import pandas as pd
    accts = []; cash = {}; fees = 0.0; paid_tot = 0.0; bought = 0; blown = 0; live = 0; worst_day = 0.0; stuck = 0
    for i, d in enumerate(dates):
        m = str(d)[:7]; cash.setdefault(m, 0.0)
        if len([a for a in accts if a.end is None]) < slots:                # buy one new evaluation per day while a slot is free
            accts.append(Account(P)); cash[m] -= P["fee"]; fees += P["fee"]; bought += 1
        day_tot = 0.0
        for a in accts:
            if a.end is not None: continue
            got = a.step(day_pts[i], day_worst[i], size_fn)
            day_tot += a.last_pnl
            if getattr(a, "passed_now", False):
                a.passed_now = False; cash[m] -= P.get("activation", 0); fees += P.get("activation", 0)
            cash[m] += got; paid_tot += got
            if a.end == "blown": blown += 1
            if a.end == "live": live += 1
            if a.end == "stuck": stuck += 1
        worst_day = min(worst_day, day_tot)
    s = pd.Series(cash)
    return {"plan": P["id"], "months": len(s), "avg_month": round(float(s.mean()), 1), "median_month": round(float(s.median()), 1),
            "worst_month": round(float(s.min()), 1), "best_month": round(float(s.max()), 1), "positive_months": round(float((s > 0).mean()), 2),
            "total": round(float(s.sum()), 0), "fees": round(fees, 0), "payouts": round(paid_tot, 0), "evals_bought": bought,
            "blown": blown, "reached_live": live, "worst_day_all_accounts": round(float(worst_day), 0), "stuck": stuck}
