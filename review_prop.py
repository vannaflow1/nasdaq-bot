"""review_prop.py - the IMMEDIATE review of a strategy that just passed the locked prop exam (no more waiting for Sunday).

The goal is a prop algo that passes evaluations and keeps paying out (in the simulator, on unseen years). An exam pass
can still be luck, or come from the prop rules + sizing rather than from the strategy. Four mechanical checks decide:
  1. PLACEBO ON THE UNSEEN YEARS: the same plan, sizing, stop and target, but entries at a random minute (same side) or a
     coin-flip side - on the 2024-26 exam days. If random entries pay about as much (p >= 0.10), the payouts are not
     coming from the strategy -> FLUKE.
  2. STABILITY: payouts minus fee per eval in four separate periods (2014-16, 2017-19, 2020-22, 2023-26) on the same
     plan and sizing. Positive in at least 3 of 4 -> stable; else FRAGILE.
  3. NUDGES: stop and target +-20%, entry window/time shifted +-15 min (all 2014-2026). EV per eval must stay > 0 in at
     least 75% of the nudges; else FRAGILE (a real effect does not depend on the exact numbers).
  4. COSTS: 1.5x commissions and slippage on the exam years must still pay out more than the fee; else FRAGILE.
All four -> CONFIRMED. Volta's nightly Claude session double-checks every automatic review and may overturn it."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

PERIODS = [(2014, 2016), (2017, 2019), (2020, 2022), (2023, 2026)]


def _ev(S, T, M, spec, plan):
    return S.prop_score(T, M, spec, plan)[0]["ev_per_eval"] if len(T) >= 30 else None


def review(spec, X, plan, exam_ev=None, reps=40, seed=3):
    import strategy_lab as S
    D = S.data(spec.get("market")); M = D["M"]; yr = M.session.str[:4].astype(int).values
    exam = np.where(M.session >= S.EXAM_FROM)[0]; allidx = np.arange(len(M))
    det, fails = {}, []
    # 1. placebo on the unseen exam years (the exam is re-scored under TODAY's simulator rules - rules get corrected over time)
    E = S.backtest(spec, X, exam); rng = np.random.default_rng(seed); e = spec["entry"]
    exam_ev = _ev(S, E, M, spec, plan) if len(E) >= 30 else -999
    det["exam_ev_now"] = round(float(exam_ev), 1)
    if exam_ev <= 0:
        return "FLUKE", f"under the current simulator rules the unseen 2024-26 years no longer pay out ({exam_ev:+.0f}$/eval)", det
    lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
    hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2); evs = []
    for r in range(reps):
        rows = []
        for s_, i, sd in zip(E.session.values, E.i.values, E.side.values):
            side = int(sd) if r % 2 == 0 else int(rng.choice([-1, 1]))           # even: random minute; odd: coin-flip side
            k = int(rng.integers(lo, hi)) if r % 2 == 0 else int(E.k[E.i == i].iloc[0])
            x = S.simulate_session(D, int(i), spec, entry_override=(k, side))
            if x: rows.append((s_, i, x[0], x[1], x[2], x[3]))
        P = pd.DataFrame(rows, columns=["session", "i", "pnl", "R", "side", "k"])
        evs.append(_ev(S, P, M, spec, plan) if len(P) >= 30 else -999)
    p = float((np.array(evs) >= exam_ev).mean())
    det["placebo_unseen"] = {"strategy_ev": round(float(exam_ev), 1), "random_mean_ev": round(float(np.mean(evs)), 1),
                             "random_p90_ev": round(float(np.percentile(evs, 90)), 1), "p": round(p, 3)}
    if p >= 0.10:
        reason = (f"random entries with the same plan/sizing/stop/target on the unseen 2024-26 days pay about as much "
                  f"(random EV {np.mean(evs):+.0f}, 90th pct {np.percentile(evs, 90):+.0f} vs {exam_ev:+.0f}; p={p:.2f}) - "
                  f"the payouts come from the prop rules and that period, not from the strategy")
        return "FLUKE", reason, det
    # 2. stability across four periods (same plan and sizing)
    T = S.backtest(spec, X, allidx); Ty = T.session.str[:4].astype(int)
    per = {f"{a}-{b}": _ev(S, T[(Ty >= a) & (Ty <= b)], M, spec, plan) for a, b in PERIODS}
    det["periods"] = per; pos = sum(1 for v in per.values() if v is not None and v > 0)
    if pos < 3: fails.append(f"payouts positive in only {pos}/4 periods ({', '.join(f'{k} {v:+.0f}' for k, v in per.items() if v is not None)})")
    # 3. nudges
    nudges = {"stop -20%": dict(stop_mult=0.8), "stop +20%": dict(stop_mult=1.2), "target -20%": dict(tgt_mult=0.8), "target +20%": dict(tgt_mult=1.2)}
    res = {}
    for name, kw in nudges.items():
        res[name] = _ev(S, S.backtest(spec, X, allidx, **kw), M, spec, plan)
    for dm in (-15, 15):
        sp = dict(spec, entry=dict(spec["entry"]))
        if sp["entry"]["type"] == "time":
            t = min(max(S.mins(sp["entry"]["at"]) + dm, 1), 380); sp["entry"]["at"] = f"{(510 + t) // 60:02d}:{(510 + t) % 60:02d}"
            res[f"entry {dm:+d} min"] = _ev(S, S.backtest(sp, X, allidx), M, sp, plan)
        else:
            res[f"window {dm:+d} min"] = _ev(S, S.backtest(spec, X, allidx, win_shift=dm), M, spec, plan)
    det["nudges"] = res; ok = sum(1 for v in res.values() if v is not None and v > 0)
    if ok < 0.75 * len(res): fails.append(f"only {ok}/{len(res)} nudges still pay out ({', '.join(f'{k} {v:+.0f}' for k, v in res.items() if v is not None)})")
    # 4. costs x1.5 on the exam years
    c = _ev(S, S.backtest(spec, X, exam, cost_mult=1.5), M, spec, plan); det["exam_costs_1.5x"] = c
    if c is None or c <= 0: fails.append(f"with 1.5x costs the unseen years pay {c if c is None else round(c)}$/eval")
    if fails:
        return "FRAGILE", "; ".join(fails), det
    return "CONFIRMED", (f"beats random entries on the unseen years (p={p:.2f}), pays out in {pos}/4 periods, {ok}/{len(res)} nudges, "
                         f"survives 1.5x costs ({c:+.0f}$/eval)"), det


def review_entry(e):
    """Review one strategies.jsonl entry (dict). Returns the fields to add."""
    import strategy_lab as S, test_engine as TE
    _, X = TE.frame()
    plan = (e.get("prop_exam") or {}).get("plan") or (e.get("prop") or [{}])[0].get("plan")
    ev = (e.get("prop_exam") or {}).get("ev_per_eval", 0)
    label, why, det = review(e["spec"], X, plan, ev)
    return {"review": f"{label} (auto, {pd.Timestamp.now(tz='UTC'):%Y-%m-%d}): {why}", "review_detail": det}


if __name__ == "__main__":                                     # review every exam-passer that has no review yet (or all with --all)
    import json, strategy_lab as S
    L = [json.loads(l) for l in open(S.LOG) if l.strip()]
    for e in L:
        if str(e.get("verdict", "")).startswith("PROMISING STRATEGY") and ("--all" in sys.argv or not e.get("review")):
            e.update(review_entry(e)); print(e["name"][:70], "->", e["review"][:400])
    with open(S.LOG, "w") as f:
        for e in L: f.write(json.dumps(e) + "\n")
