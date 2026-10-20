"""prop_sim.py - Lucid prop-firm simulator. Volta's objective since 2026-10-20: maximise PAYOUTS minus eval fees.

Takes a strategy's real day-by-day results on NQ (points per contract after costs, from strategy_lab.backtest on
1-minute bars) and runs complete prop accounts through them in historical order, starting on every possible day:
evaluation -> funded -> payouts, with Lucid's rules (sources: Lucid rule guides, Sep-Oct 2026 - re-check on Lucid's site):

LucidFlex 25K   eval: target +$1,250, end-of-day trailing max loss $1,000 (locks at $25,100), no daily limit,
                      50% consistency (largest day <= 50% of total profit), max 2 NQ / 20 MNQ
                funded: same trailing max loss, no consistency; size scales 1 NQ/10 MNQ (profit < $1,000) -> 2/20;
                      payout after 5 days with >= $100 profit and positive cycle profit; request 50% of profit,
                      max $1,000, min $500; trader keeps 90%; 5 payouts -> live review (simulation stops: success)
LucidPro 25K    eval: same target/loss; funded: 40% consistency, payout after a cycle profit of $250 and 3 days,
                      payout 1 max $1,000 then $1,500, buffer: balance must stay >= MLL + $100 after the payout
The max loss is checked against the worst point of each trade (stop-based trades: the stop loss), not just the close.
"""
import numpy as np, pandas as pd
MNQ, NQ = 2.0, 20.0

PLANS = {
    "flex25": dict(size=25_000, target=1_250, mll=1_000, eval_consistency=0.50, eval_max=20, fund_consistency=None,
                   fund_max=lambda profit: 10 if profit < 1_000 else 20, payout_days=5, day_min=100, cycle_min=0,
                   payout_frac=0.50, caps=[1_000] * 5, min_req=500, buffer=0),
    "pro25": dict(size=25_000, target=1_250, mll=1_000, eval_consistency=None, eval_max=20, fund_consistency=0.40,
                  fund_max=lambda profit: 20, payout_days=3, day_min=0, cycle_min=250,
                  payout_frac=1.0, caps=[1_000, 1_500, 1_500, 1_500, 1_500], min_req=500, buffer=100),
}


def run_account(day_pts, day_worst, start, plan, size_fn, max_days=400):
    """One account from day index `start`. day_pts[i] = points per MNQ that day (0 = no trade), day_worst[i] = worst
    open loss in points per MNQ (<= 0). size_fn(phase, profit, buffer) -> MNQ contracts.
    Returns dict(passed, payouts (list of $ paid to the trader), days, end) ."""
    P = PLANS[plan]; S0 = P["size"]
    bal = peak = float(S0); floor = S0 - P["mll"]; phase = "eval"; days = 0
    eval_days = []; payouts = []; cycle_days = []; cycle_start = bal
    for i in range(start, min(len(day_pts), start + max_days)):
        days += 1
        profit = bal - S0
        cap = P["eval_max"] if phase == "eval" else P["fund_max"](profit)
        n = int(min(cap, max(0, size_fn(phase, profit, bal - floor))))
        pnl = n * day_pts[i] * MNQ; worst = n * day_worst[i] * MNQ
        if bal + worst <= floor:                                  # touched the max loss intraday
            return dict(passed=phase == "funded", payouts=payouts, days=days, end="blown")
        bal += pnl
        if phase == "eval":
            eval_days.append(pnl)
            tot = bal - S0
            if tot >= P["target"]:
                big = max(eval_days)
                if P["eval_consistency"] is None or big <= P["eval_consistency"] * tot:
                    phase = "funded"; bal = peak = float(S0); floor = S0 - P["mll"]; cycle_days = []; cycle_start = bal
                    continue
        else:
            cycle_days.append(pnl)
            prof_cycle = bal - cycle_start; profit = bal - S0
            ok_days = sum(d >= max(P["day_min"], 0.01) for d in cycle_days)
            cons_ok = True
            if P["fund_consistency"] and prof_cycle > 0:
                cons_ok = max(cycle_days) <= P["fund_consistency"] * prof_cycle
            if ok_days >= P["payout_days"] and prof_cycle > max(P["cycle_min"], 0) and cons_ok and profit > 0:
                req = min(P["payout_frac"] * profit, P["caps"][min(len(payouts), len(P["caps"]) - 1)],
                          bal - floor - P["buffer"])
                if req >= P["min_req"]:
                    bal -= req; payouts.append(0.9 * req); cycle_days = []; cycle_start = bal
                    if len(payouts) >= 5:
                        return dict(passed=True, payouts=payouts, days=days, end="live")
        peak = max(peak, bal)                                     # end-of-day trailing max loss
        floor = max(floor, min(peak - P["mll"], S0 + 100))
    return dict(passed=phase == "funded", payouts=payouts, days=days, end="timeout")


def evaluate(day_pts, day_worst, plan="flex25", size_fn=None, fee=0.0, starts=None, step=3):
    size_fn = size_fn or (lambda phase, profit, buf: 2)
    starts = range(0, len(day_pts) - 60, step) if starts is None else starts
    R = [run_account(day_pts, day_worst, s, plan, size_fn) for s in starts]
    pay = np.array([sum(r["payouts"]) for r in R]); passed = np.array([r["passed"] for r in R])
    return {"accounts": len(R), "pass_rate": round(float(passed.mean()), 3),
            "avg_payout_per_eval": round(float(pay.mean()), 1), "ev_per_eval": round(float(pay.mean() - fee), 1),
            "share_with_payout": round(float((pay > 0).mean()), 3), "reach_live": round(float(np.mean([r["end"] == "live" for r in R])), 3),
            "median_days": int(np.median([r["days"] for r in R]))}
