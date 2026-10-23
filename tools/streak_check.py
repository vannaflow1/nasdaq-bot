"""tools/streak_check.py - wish #11 (23 Oct 2026): does sizing up after consecutive profit days help?

Read-only diagnostic. Streak (anti-martingale) sizing can only raise expected R per unit of risk if a day's result
depends on the previous days' results. With independent days it only reshapes the variance (bigger swings, same edge per
unit risked). This tool measures that dependence on a family's frozen variant over the ALREADY-SEEN years
(search 2014-21 + validation 2022-23; never the 2024-now exam, never forward days), with a day-shuffle permutation test,
and compares flat sizing with the proposed streak rule on the same days.
It changes nothing: no family, no frozen design, no sizing in prop_sim / the forward test.
Run: python tools/streak_check.py [--id F10] [--reps 5000]   -> knowledge/research_out/streak_check.json"""
import json, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
LO, HI = "2014-01-01", "2023-12-31"


def streaks(win):
    """Number of consecutive profitable days BEFORE each day (0 for the first day)."""
    s, out = 0, np.zeros(len(win), int)
    for t in range(len(win)):
        out[t] = s; s = s + 1 if win[t] else 0
    return out


def stats(r):
    win = r > 0; k = streaks(win); prev = np.r_[np.nan, r[:-1]]
    ac1 = float(np.corrcoef(r[1:], r[:-1])[0, 1]) if len(r) > 2 else np.nan
    after2 = r[k >= 2].mean() if (k >= 2).any() else np.nan; other = r[k < 2].mean() if (k < 2).any() else np.nan
    size = np.minimum(1.0 + 0.5 * np.maximum(k - 1, 0), 2.0)        # proposed rule: +0.5x per profit day after the first, cap 2x
    return {"ac1": ac1, "after2": float(after2), "other": float(other), "gap": float(after2 - other),
            "edge_flat": float(r.mean()), "edge_streak_per_risk": float((size * r).sum() / size.sum()),
            "n_after2": int((k >= 2).sum())}


def maxdd(x):
    c = np.cumsum(x); return float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max())


def main():
    import strategy_lab as S, test_engine as TE, families as FA
    fid = sys.argv[sys.argv.index("--id") + 1] if "--id" in sys.argv else "F10"
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 5000
    fam = [f for f in json.load(open(FA.REG)) if f["id"] == fid][0]
    v = FA.variants(fam)[int(fam.get("forward_variant", 0))]
    _, X = TE.frame()
    T = FA.trades(S, X, v["sleeve"], LO, HI)
    r = T.groupby("session").R.sum().sort_index().to_numpy(float)
    obs = stats(r); rng = np.random.default_rng(7); null_gap, null_ac = [], []
    for _ in range(reps):
        p = stats(rng.permutation(r)); null_gap.append(p["gap"]); null_ac.append(p["ac1"])
    null_gap, null_ac = np.array(null_gap), np.array(null_ac)
    k = streaks(r > 0); size = np.minimum(1.0 + 0.5 * np.maximum(k - 1, 0), 2.0)
    out = {"family": fid, "variant": int(fam.get("forward_variant", 0)), "params": v.get("params"), "window": [LO, HI],
           "days": int(len(r)), "trades": int(len(T)), **{k_: round(v_, 4) if isinstance(v_, float) else v_ for k_, v_ in obs.items()},
           "p_gap_one_sided": float((1 + (null_gap >= obs["gap"]).sum()) / (reps + 1)),
           "p_ac1_two_sided": float((1 + (np.abs(null_ac) >= abs(obs["ac1"])).sum()) / (reps + 1)),
           "maxdd_R_flat": round(maxdd(r), 2), "maxdd_R_streak": round(maxdd(size * r), 2),
           "mean_size_streak": round(float(size.mean()), 3), "reps": reps,
           "rule": "size = min(1 + 0.5*(profit-day streak - 1), 2); flat = 1"}
    json.dump(out, open(os.path.join(HERE, "knowledge", "research_out", "streak_check.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
