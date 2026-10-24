"""tools/speed_check.py - the fast-track speed metric (knowledge/frozen/epoch_fast.json, owner OK 24 Oct 2026).

For a family's forward variant (its 2022-now trades = the SHAPE: stops, skew, trades per day), the true edge is set to
HALF its validation edge (shrunk - validation is optimistic). For every Lucid plan x sizing, block-bootstrapped account
paths (eval_decision.run_paths, Lucid's real commission) give: E[EV per eval], median days to first payout, account life,
and $ per month per account slot = EV / life x 21.
QUALIFIES (frozen rule) if some setup has median days to first payout <= 30 AND E[EV per eval] > 0.
Run: python tools/speed_check.py F13"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
SIZINGS = (0.08, 0.12, 0.2, 0.3, 0.5)


def check(fid, X=None):
    import eval_decision as ED, strategy_lab as S, prop_sim as PS, sealed as SE
    T, R, st, ses = ED.shape(fid)
    val = SE.edge_days(T.assign(R=R), B=500)["edge"]; edge = 0.5 * float(val)
    plans = PS.plans(True); med = float(np.median(st)); pts, wst = ED.day_series(T, R, st, ses, edge); rows = []
    for plan in ED.PLANS:
        for risk in SIZINGS:
            fn = S._sizer({"target": {"R": 5}, "prop": {"risk": risk, "eval_risk": risk, "eval_finish": True}}, med)
            r = ED.run_paths(pts, wst, plans[plan], fn, seed=int(risk * 1000))
            life = max(r["median_account_life_days"], 1)
            rows.append({"plan": plan, "risk": risk, **r, "usd_per_month_per_slot": round(r["ev_per_eval"] / life * 21, 1)})
    fast = [r for r in rows if (r["median_days_to_first_payout"] or 999) <= 30 and r["ev_per_eval"] > 0]
    best = max(rows, key=lambda r: r["usd_per_month_per_slot"])
    out = {"family": fid, "validation_edge": round(float(val), 4), "edge_used_half": round(edge, 4), "trades": int(len(T)),
           "trades_per_session": round(len(T) / max(len(ses), 1), 2), "qualifies": bool(fast),
           "best_fast": max(fast, key=lambda r: r["ev_per_eval"]) if fast else None, "best_per_month": best, "rows": rows}
    os.makedirs(os.path.join(HERE, "knowledge", "research_out"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "knowledge", "research_out", f"speed_{fid}.json"), "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    o = check(sys.argv[1] if len(sys.argv) > 1 else "F10")
    print({k: v for k, v in o.items() if k != "rows"})
