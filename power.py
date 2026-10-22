"""power.py - can Volta's family test find a real edge at all? (expert review, 21 Oct 2026, upgrade 3; null v3 22 Oct 2026)

NULL WORLDS (v3): the family's real trades on its validation window are re-run with ONE shared random draw per
market-session for every variant (side reversed on a random half of the sessions; or, where the side is known before the
session, the same side at one random minute) - exactly the null the family test uses (families.null_draws). A null world
has no edge by construction but keeps everything else: the same days, stops, trade counts and - the point of v3 - the
same strong correlation between variants.
v2 (until 22 Oct) let independent coin flips per variant pose as "the strategy" AND form the null. Averaged over 50 variants
those are 3-4x too smooth, so its "0% false passes" was guaranteed by construction and its power was overstated.
A known edge is PLANTED: +delta R on every trade of a random 60% of the market-sessions, the same sessions for every
variant (a real edge moves all variants together; average lift 0.6 x delta - deliberately noisy).
  false-pass rate = share of null worlds the family test passes (must stay near alpha)
  power(delta)    = share of planted worlds it passes, at the alpha the NEXT family would face (and at 0.05 for context)
Results: knowledge/research_out/power.csv; the curve is the scoreboard (status.json["power"]).
Run: python power.py [--family F10] [--worlds 400]"""
import json, os, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
DELTAS = [0.05, 0.10, 0.20]


def main():
    import strategy_lab as S, test_engine as TE, families as F, sealed as SE
    fid = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else "F10"
    worlds = int(sys.argv[sys.argv.index("--worlds") + 1]) if "--worlds" in sys.argv else 400
    fam = next(f for f in json.load(open(F.REG)) if f["id"] == fid)
    _, X = TE.frame(); seed = int(time.time()) % 10**6; rng = np.random.default_rng(seed)
    L = F.ledger(); j_next = int((L.get("rules", pd.Series(dtype=str)).astype(str) == "v2").sum()) + 1 if len(L) else 1
    alpha = SE.alpha_v2(j_next)                                  # the alpha the next v2 family would be tested at
    hi = "2099-12-31" if fam.get("rules") == "v2" else F.B_END
    V = F.variants(fam); TB = [F.trades(S, X, v["sleeve"], "2022-01-01", hi) for v in V]
    ok = [i for i, t in enumerate(TB) if len(t) >= 20]
    if len(ok) < 5: print("too few trades"); return
    t0 = time.time(); tabs = [F.twin_tables(S, TB[i]) for i in ok]
    stat = lambda xs: float(np.median([np.nanmean(x) for x in xs]))
    null = F.null_draws(tabs, stat, reps=F.NULL_REPS, seed=seed + 1)   # also sets t["ki"] (market-session index)
    nK = 1 + max(int(t["ki"].max()) for t in tabs if len(t["ki"]))
    has_m = any(t["Rm"] is not None for t in tabs); rows = []
    for w in range(worlds):
        c = rng.random(nK) < 0.5; lift = rng.random(nK) < 0.6
        mb = rng.integers(0, F.MINUTE_BINS, nK) if (has_m and w % 2 == 1) else None
        xs = []
        for t in tabs:
            x = np.where(c[t["ki"]], t["R0"], t["R1"])
            if mb is not None and t["Rm"] is not None:
                xm = t["Rm"][np.arange(len(x)), mb[t["ki"]]]; x = np.where(np.isfinite(xm), xm, x)
            xs.append(x)
        for d in [0.0] + DELTAS:
            means = np.array([np.nanmean(x + d * lift[t["ki"]]) for x, t in zip(xs, tabs)])
            m = float(np.median(means)); share = float(np.mean(means > 0)); p = F.null_p(m, null)
            rows.append({"date": datetime.now(timezone.utc).date().isoformat(), "family": fid, "method": "shared-null-v3",
                         "world": w, "delta": d, "median_B": m, "share_pos": share, "p": p, "alpha": alpha,
                         "passed": bool(m > 0 and share >= 0.6 and p < alpha), "passed_at_05": bool(m > 0 and share >= 0.6 and p < 0.05)})
    R = pd.DataFrame(rows); os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
    fn = os.path.join(K, "research_out", "power.csv")
    old = pd.read_csv(fn) if os.path.exists(fn) else pd.DataFrame()
    pd.concat([old, R], ignore_index=True).to_csv(fn, index=False)
    curve = R.groupby("delta").passed.mean(); c05 = R.groupby("delta").passed_at_05.mean()
    print(f"{len(ok)} variants, {worlds} worlds, null sd {null.std():.4f}R around {null.mean():+.4f}R, {time.time() - t0:.0f}s")
    lines = [f"⚡ POWER CURVE - THE SCOREBOARD (family {fid} trades, null v3 with shared draws, {worlds} worlds): can my family test find a planted edge?",
             f"False passes with no edge: {curve.get(0.0, float('nan')):.1%} (alpha for the next family {alpha:.4f})",
             "Found a planted edge at that alpha: " + ", ".join(f"+{d:.2f}R {curve.get(d, float('nan')):.0%}" for d in DELTAS)
             + " | at alpha 0.05: " + ", ".join(f"+{d:.2f}R {c05.get(d, float('nan')):.0%}" for d in DELTAS)
             + " (planted on 60% of sessions, all variants together: true lift 0.6x)",
             "The edge has to clear the costs first: a no-edge world sits at the no-information level "
             f"({null.mean():+.3f}R), not at 0."]
    s = json.load(open(os.path.join(HERE, "status.json"))) if os.path.exists(os.path.join(HERE, "status.json")) else {}
    s["power"] = lines; json.dump(s, open(os.path.join(HERE, "status.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
