"""power.py - can Volta's family test find a real edge at all? (expert review, 21 Oct 2026, upgrade 3)

For a reference family, many NULL WORLDS are built: the daily feature table is shuffled across days in 20-day blocks, which
breaks the link between Volta's predictors (filters, direction formulas) and what the market did next, while keeping
both distributions. In each null world the family test is run exactly as families.py runs it (median validation edge
across all variants vs a placebo family). Then a known edge is PLANTED: +delta R added to the family's trades on a random
60% of days (so the average lift is 0.6*delta - deliberately noisy), and the test is run again on the same world.
  false-pass rate = share of null worlds the test passes (must stay near alpha; much higher = a leak or a bug)
  power(delta)    = share of planted worlds the test passes
The power curve is the scoreboard (status.json["power"]): if Volta cannot find a planted +0.10R edge, more search cannot
help - it needs more trades per test (more markets, more trades per day). Results: knowledge/research_out/power.csv.
Run: python power.py [--family F5] [--worlds 20] [--reps 40]"""
import json, os, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
DELTAS = [0.05, 0.10, 0.20]


def shuffle_X(X, rng, block=20):
    n = len(X); starts = np.arange(0, n, block); rng.shuffle(starts)
    order = np.concatenate([np.arange(s, min(s + block, n)) for s in starts])[:n]
    Y = X.iloc[order].copy(); Y.index = X.index
    return Y


def world_stats(fam, X, S, rng, reps):
    import families as F
    V = F.variants(fam); TB = []
    for v in V: TB.append(F.trades(S, X, v["sleeve"], "2022-01-01", F.B_END))
    ok = [i for i, t in enumerate(TB) if len(t) >= 20]
    if len(ok) < 5: return None
    pl = []
    for j in range(reps):
        m = [F.placebo_mean(S, TB[i], rng, j) for i in ok]; m = [x for x in m if np.isfinite(x)]
        if m: pl.append(float(np.median(m)))
    pl = np.array(pl)
    out = {}
    for d in [0.0] + DELTAS:
        med = []; pos = []
        for i in ok:
            R = TB[i].R.values.astype(float)
            if d: R = R + d * (rng.random(len(R)) < 0.6)
            med.append(R.mean()); pos.append(R.mean() > 0)
        mB = float(np.median(med)); p = float((pl >= mB).mean())
        out[d] = {"median": mB, "share_pos": float(np.mean(pos)), "p": p}
    return out


def main():
    import strategy_lab as S, test_engine as TE, families as F
    fid = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else "F5"
    worlds = int(sys.argv[sys.argv.index("--worlds") + 1]) if "--worlds" in sys.argv else 20
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 40
    fam = next(f for f in json.load(open(F.REG)) if f["id"] == fid)
    _, X = TE.frame(); rng = np.random.default_rng(int(time.time()) % 10**6)
    alpha = F.ALPHA / max(1, len(F.ledger()))
    rows = []
    for w in range(worlds):
        st = world_stats(fam, shuffle_X(X, rng), S, rng, reps)
        if not st: continue
        for d, r in st.items():
            rows.append({"date": datetime.now(timezone.utc).date().isoformat(), "family": fid, "world": w, "delta": d,
                         "median_B": r["median"], "share_pos": r["share_pos"], "p": r["p"],
                         "passed": bool(r["median"] > 0 and r["share_pos"] >= 0.6 and r["p"] < alpha)})
        print(f"world {w}: " + ", ".join(f"+{d:.2f}R p={r['p']:.2f}" for d, r in st.items()), flush=True)
    R = pd.DataFrame(rows); os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
    fn = os.path.join(K, "research_out", "power.csv")
    old = pd.read_csv(fn) if os.path.exists(fn) else pd.DataFrame()
    pd.concat([old, R], ignore_index=True).to_csv(fn, index=False)
    curve = R.groupby("delta").passed.mean()
    lines = [f"⚡ POWER CURVE (can my family test find a planted edge? {fid}, {R.world.nunique()} null worlds, alpha {alpha:.3f}) - THE SCOREBOARD",
             f"False passes with no edge: {curve.get(0.0, float('nan')):.0%} (should stay near {alpha:.0%}; much higher = a leak or bug)",
             "Found a planted edge: " + ", ".join(f"+{d:.2f}R {curve.get(d, float('nan')):.0%}" for d in DELTAS) + " (planted on 60% of trades, so the true lift is 0.6x that)",
             "Below ~20% at +0.10R: more search cannot help - I need more trades per test (more markets, more trades per day)."]
    s = json.load(open(os.path.join(HERE, "status.json"))) if os.path.exists(os.path.join(HERE, "status.json")) else {}
    s["power"] = lines; json.dump(s, open(os.path.join(HERE, "status.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
