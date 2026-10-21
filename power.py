"""power.py - can Volta's family test find a real edge at all? (expert review, 21 Oct 2026, upgrade 3)

NULL WORLDS (v2, 21 Oct): for every variant of a family, R draws of no-edge "twins" are simulated on the validation days
(the same placebo construction families.py uses: random minute with the same side, or the same minute with a coin-flip
side; coin-flip only when the direction is decided during the session). In world w, twin draw w POSES AS THE STRATEGY and
the family test is run against the other draws - a world with no edge by construction, for every kind of family (v1
shuffled the feature table, which leaves price-only families such as F2 untouched - its null worlds still had the edge).
A known edge is then PLANTED: +delta R on a random 60% of the posing trades (average lift 0.6*delta - deliberately noisy).
  false-pass rate = share of null worlds the test passes (must stay near alpha; much higher = a bug)
  power(delta)    = share of planted worlds the test passes
The power curve is the scoreboard (status.json["power"]). Results: knowledge/research_out/power.csv.
Run: python power.py [--family F2] [--worlds 40]"""
import json, os, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
DELTAS = [0.05, 0.10, 0.20]


def twin_R(S, T, rng, j):
    """All R values of one no-edge twin of trades T (same rule as families.placebo_mean)."""
    import families as F
    Rs = []
    for spec_s, g in T.groupby("spec"):
        sp = json.loads(spec_s); D = S.data(sp.get("market")); e = sp["entry"]
        lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
        hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(sp.get("exit", "14:55")) - 5, 380)
        lo, hi = max(lo, 1), max(hi, lo + 2); intraday = F.intraday_side(sp)
        for i, sd, k in zip(g.i.values, g.side.values, g.k.values):
            ov = (int(rng.integers(lo, hi)), int(sd)) if (j % 2 == 0 and not intraday) else (int(k), int(rng.choice([-1, 1])))
            r = S.simulate_session(D, int(i), sp, entry_override=ov)
            if r: Rs.append(r[1])
    return np.array(Rs, float)


def main():
    import strategy_lab as S, test_engine as TE, families as F
    fid = sys.argv[sys.argv.index("--family") + 1] if "--family" in sys.argv else "F2"
    worlds = int(sys.argv[sys.argv.index("--worlds") + 1]) if "--worlds" in sys.argv else 40
    fam = next(f for f in json.load(open(F.REG)) if f["id"] == fid)
    _, X = TE.frame(); rng = np.random.default_rng(int(time.time()) % 10**6)
    alpha = F.ALPHA / max(1, len(F.ledger()))
    V = F.variants(fam); TB = [F.trades(S, X, v["sleeve"], "2022-01-01", F.B_END) for v in V]
    ok = [i for i, t in enumerate(TB) if len(t) >= 20]
    if len(ok) < 5: print("too few trades"); return
    draws = worlds + 60                                       # twin draws: `worlds` pose as the strategy, the rest form the test
    t0 = time.time()
    tw = [[twin_R(S, TB[i], rng, j) for i in ok] for j in range(draws)]      # tw[draw][variant] -> R array
    med = np.array([np.median([x.mean() for x in d if len(x) >= 20]) for d in tw])
    print(f"{draws} twin draws x {len(ok)} variants in {time.time() - t0:.0f}s; twin median mean {med.mean():+.3f}R")
    rows = []
    for w in range(worlds):
        others = np.delete(med, w)
        for d in [0.0] + DELTAS:
            means = []
            for x in tw[w]:
                if len(x) < 20: continue
                y = x + d * (rng.random(len(x)) < 0.6); means.append(y.mean())
            m = float(np.median(means)); share = float(np.mean(np.array(means) > 0)); p = float((others >= m).mean())
            rows.append({"date": datetime.now(timezone.utc).date().isoformat(), "family": fid, "method": "twin-null-v2", "world": w,
                         "delta": d, "median_B": m, "share_pos": share, "p": p,
                         "passed": bool(m > 0 and share >= 0.6 and p < alpha)})
    R = pd.DataFrame(rows); os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
    fn = os.path.join(K, "research_out", "power.csv")
    old = pd.read_csv(fn) if os.path.exists(fn) else pd.DataFrame()
    pd.concat([old, R], ignore_index=True).to_csv(fn, index=False)
    curve = R.groupby("delta").passed.mean(); pval = R.groupby("delta").p.median()
    lines = [f"⚡ POWER CURVE - THE SCOREBOARD (family {fid}, {worlds} no-edge worlds, alpha {alpha:.3f}): can my family test find a planted edge?",
             f"False passes with no edge: {curve.get(0.0, float('nan')):.0%} (should stay near {alpha:.1%}; much higher = a bug)",
             "Found a planted edge: " + ", ".join(f"+{d:.2f}R {curve.get(d, float('nan')):.0%} (median p {pval.get(d, float('nan')):.2f})" for d in DELTAS)
             + " (planted on 60% of trades: true lift 0.6x)",
             "Below ~20% at +0.10R: more search cannot help - I need more trades per test (more markets, more trades per day)."]
    s = json.load(open(os.path.join(HERE, "status.json"))) if os.path.exists(os.path.join(HERE, "status.json")) else {}
    s["power"] = lines; json.dump(s, open(os.path.join(HERE, "status.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
