"""tools/quantleak_studies.py - three read-only studies prompted by quantleak.zip (27 Nov 2026, owner request)

All on the ALREADY-SEEN years 2014-2023 (search + validation), never the 2024-now exam and never forward days, on each
forward family's frozen forward variant. Nothing here changes a family, a frozen design, an alpha slot or eta's inputs;
every result is a post-hoc observation (hypothesis), not a finding - acting on one needs its own frozen rule (owner).

A. Volatility-managed sizing (Moreira & Muir 2017, JF): size_t = expanding median(rv20 before t) / rv20_t, clipped
   [0.25, 2], using the 20-day realised vol known at the PREVIOUS close (test_engine's X row of the prior date, so no
   lookahead). Same with 30-day implied vol (iv30) at the previous close. Compared with flat
   sizing on edge per unit risked (sum w*R / sum w), daily Sharpe and max drawdown; p = day-shuffle of the weights.
B. Deflated Sharpe ratio (Bailey & Lopez de Prado 2014) of the variant's per-trade R on 2022-23, for N = its family's
   grid size and N = every variant Volta's families ever scored. Non-normality (skew, kurtosis) included.
C. Growth/drawdown at fractional Kelly (knowledge/research_out/sizing.json): stationary block bootstrap of the daily R
   (mean block 10 days) RECENTRED so the mean per trade equals today's posterior mean (not the in-sample edge),
   one year = 252 sessions, compounding at f of capital per -1R. Reports annual return and max-drawdown percentiles.
Run: python tools/quantleak_studies.py [--reps 5000]   -> knowledge/research_out/quantleak_studies.json"""
import json, math, os, sys
import numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
K = os.path.join(HERE, "knowledge")
LO, HI, B_LO = "2014-01-01", "2023-12-31", "2022-01-01"


def maxdd(x):
    c = np.cumsum(x); return float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max())


def vol_sizing(day, col, rng, reps):
    v = day[col].to_numpy(float); r = day["R"].to_numpy(float)
    med = pd.Series(v).expanding().median().shift(1).to_numpy()
    w = np.clip(med / v, 0.25, 2.0); ok = np.isfinite(w); w, r = w[ok], r[ok]
    f = lambda ww: float((ww * r).sum() / ww.sum())
    obs = f(w) - r.mean()
    null = np.array([f(rng.permutation(w)) - r.mean() for _ in range(reps)])
    sh = lambda x: float(x.mean() / x.std(ddof=1) * math.sqrt(252))
    return {"days": int(ok.sum()), "edge_per_risk_flat": round(float(r.mean()), 4), "edge_per_risk_managed": round(f(w), 4),
            "gain": round(obs, 4), "p_one_sided": round(float((1 + (null >= obs).sum()) / (reps + 1)), 4),
            "sharpe_daily_ann_flat": round(sh(r), 3), "sharpe_daily_ann_managed": round(sh(w * r), 3),
            "maxdd_R_flat": round(maxdd(r), 1), "maxdd_R_managed": round(maxdd(w * r / w.mean()), 1),
            "mean_weight": round(float(w.mean()), 3)}


def dsr(R, n_trials):
    n = len(R); sr = R.mean() / R.std(ddof=1); g3 = skew(R); g4 = kurtosis(R, fisher=False)
    var_sr = 1 / (n - 1)                                     # trials' SR variance approximated by the null SR variance
    e = 0.5772156649
    sr0 = math.sqrt(var_sr) * ((1 - e) * norm.ppf(1 - 1 / n_trials) + e * norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(n - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return {"trades": n, "sr_per_trade": round(float(sr), 4), "skew": round(float(g3), 3), "kurtosis": round(float(g4), 3),
            "trials": int(n_trials), "sr0_expected_max_of_noise": round(sr0, 4), "dsr_prob": round(float(norm.cdf(z)), 3)}


def block_boot(x, n, rng, mean_block=10):
    out = np.empty(n); i = rng.integers(len(x))
    for t in range(n):
        if rng.random() < 1 / mean_block: i = rng.integers(len(x))
        out[t] = x[i]; i = (i + 1) % len(x)
    return out


def kelly_paths(day, post_mean, fracs, rng, reps):
    r = day["R"].to_numpy(float); k = day["k"].to_numpy(float)
    rc = r - k * (r.sum() / k.sum() - post_mean)            # recentre: mean per TRADE = posterior mean
    res = {}
    paths = np.array([block_boot(rc, 252, rng) for _ in range(reps)])
    for name, f in fracs.items():
        eq = np.cumprod(1 + f * paths, axis=1)
        ann = eq[:, -1] - 1
        dd = 1 - (eq / np.maximum.accumulate(np.c_[np.ones(reps), eq], axis=1)[:, 1:]).min(axis=1)
        res[name] = {"risk_per_R": f, "year_return_p5": round(float(np.percentile(ann, 5)), 4),
                     "year_return_median": round(float(np.median(ann)), 4), "year_return_p95": round(float(np.percentile(ann, 95)), 4),
                     "p_losing_year": round(float((ann < 0).mean()), 3),
                     "maxdd_median": round(float(np.median(dd)), 4), "maxdd_p95": round(float(np.percentile(dd, 95)), 4)}
    return res


def main():
    import strategy_lab as S, test_engine as TE, families as FA
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 5000
    fams = json.load(open(FA.REG)); sizing = json.load(open(os.path.join(K, "research_out", "sizing.json")))["families"]
    all_trials = 0
    for f in fams:
        if f.get("status") in ("scored", "forward"):
            try: all_trials += len(FA.variants(f))
            except Exception: pass
    _, X = TE.frame(); X = X.copy()
    prev = X[["rv20", "iv30"]].shift(1)                       # X rows are known at that date's close -> use the prior row
    prev.index = pd.to_datetime(prev.index).strftime("%Y-%m-%d")
    out = {"window": [LO, HI], "note": "post-hoc, seen years only; hypotheses, not findings", "families": {}}
    for f in fams:
        if f.get("status") != "forward" or f["id"] not in sizing: continue
        vi = int(f.get("forward_variant", 0)); v = FA.variants(f)[vi]
        T = FA.trades(S, X, v["sleeve"], LO, HI); T["session"] = pd.to_datetime(T["session"]).dt.strftime("%Y-%m-%d")
        day = T.groupby("session").agg(R=("R", "sum"), k=("R", "size")).join(prev, how="left")
        rng = np.random.default_rng(7)
        z = sizing[f["id"]]
        res = {"variant": vi, "params": v.get("params"), "trades": int(len(T)), "days": int(len(day)),
               "edge_per_trade_seen": round(float(T.R.mean()), 4),
               "A_vol_managed_rv20": vol_sizing(day.dropna(subset=["rv20"]), "rv20", rng, reps),
               "A_vol_managed_iv30": vol_sizing(day.dropna(subset=["iv30"]), "iv30", rng, reps),
               "B_deflated_sharpe_2022_23": {
                   "family_grid": dsr(T[T.session >= B_LO].R.to_numpy(float), len(FA.variants(f))),
                   "all_families": dsr(T[T.session >= B_LO].R.to_numpy(float), all_trials)},
               "C_kelly_one_year": kelly_paths(day, z["posterior_mean_R"],
                                               {"quarter": z["quarter_kelly"], "half": z["half_kelly"], "full": z["kelly"]},
                                               rng, min(reps, 4000))}
        out["families"][f["id"]] = res
    json.dump(out, open(os.path.join(K, "research_out", "quantleak_studies.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
