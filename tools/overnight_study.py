"""tools/overnight_study.py - does anything known BEFORE the 08:30 CT open help the NQ day bias? (owner request 26 Oct 2026)

PRE-DECLARED before any number was looked at (this docstring is committed first):
  Data   : owner's full-session NQ 1-minute 2014 - Jan 2026 (om.days), knowledge/macro_daily.csv (prior US close),
           knowledge/data/econ_events_red.csv (release times).
  Design : 2014-01-01 .. 2021-12-31.   Holdout: 2022-01-01 .. end, looked at ONCE, after the design decision is written.
  Features (all known by 08:29 CT):
    on_ret     overnight return, prior 14:59 CT close -> 08:29 CT
    asia_ret   17:00 -> 02:00 CT          london_ret  02:00 -> 08:29 CT
    gap_loc    08:29 price vs prior RTH high/low (+1 above high, -1 below low, 0 inside)
    prev_ret   prior RTH open->close       trend5      5-session RTH close-to-close return
    on_range_z overnight high-low / median of the last 20 overnight ranges
    vix_chg, vix_term, us10y_chg_bp, dxy_ret, nq_vs_es   (prior US close)
    red_pre    a red-folder release between 07:00 and 08:29 CT today      fomc   FOMC decision day
  Targets:
    T1 RTH direction: close 14:59 vs open 08:30 (sign + return)
    T2 day size: |RTH return| / median of last 20 sessions  (a range forecast, not a direction)
    T3 the live intraday noise-band bias (bias.py rules, hourly 09-14 CT): rest-of-day hit rate split by whether the
       overnight move agrees with the band direction
  Decision rule (design period only): a feature/composite enters the live bias only if its design-period effect has
    day-level p < 0.01 AND the holdout shows the same sign with p < 0.05. Range features (T2) may be reported as
    'expected day size' with the same rule. Everything else is reported as 'no measurable effect'.
Run: python tools/overnight_study.py design      then, after writing the decision:  python tools/overnight_study.py holdout"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import om
K = os.path.join(HERE, "knowledge"); OUT = os.path.join(K, "research_out")
FEATS = ["on_ret", "asia_ret", "london_ret", "gap_loc", "prev_ret", "trend5", "on_range_z",
         "vix_chg", "vix_term", "us10y_chg_bp", "dxy_ret", "nq_vs_es", "red_pre", "fomc"]
M = om.m_of
O830, C1459, A0200, P0829 = M(8, 30), M(14, 59), M(2, 0), M(8, 29)


def table():
    D = om.days(); dates = pd.to_datetime(D["dates"]); n = len(dates)
    O, H, L, C = D["o"], D["h"], D["l"], D["c"]; ok = D["have"] > 900
    rth_o, rth_c = O[:, O830].astype(float), C[:, C1459].astype(float)
    rth_h = H[:, O830:C1459 + 1].max(1).astype(float); rth_l = L[:, O830:C1459 + 1].min(1).astype(float)
    pre = C[:, P0829].astype(float)
    prev_c = np.r_[np.nan, rth_c[:-1]]; prev_o = np.r_[np.nan, rth_o[:-1]]
    on_hi = H[:, :O830].max(1).astype(float); on_lo = L[:, :O830].min(1).astype(float); onr = (on_hi - on_lo) / pre
    T = pd.DataFrame({"date": dates, "ok": ok, "rth_ret": rth_c / rth_o - 1, "on_ret": pre / prev_c - 1,
                      "asia_ret": C[:, A0200] / np.r_[np.nan, rth_c[:-1]] - 1, "london_ret": pre / C[:, A0200] - 1,
                      "gap_loc": np.where(pre > np.r_[np.nan, rth_h[:-1]], 1, np.where(pre < np.r_[np.nan, rth_l[:-1]], -1, 0)),
                      "prev_ret": prev_c / prev_o - 1})
    T["asia_ret"] = C[:, A0200] / prev_c - 1
    T["trend5"] = pd.Series(rth_c).shift(1) / pd.Series(rth_c).shift(6) - 1
    T["on_range_z"] = pd.Series(onr) / pd.Series(onr).shift(1).rolling(20, min_periods=10).median()
    T["size_z"] = T.rth_ret.abs() / T.rth_ret.abs().shift(1).rolling(20, min_periods=10).median()
    # gap days (no prior session yesterday) make on_ret span a holiday - keep them, they are real overnight moves
    Mc = pd.read_csv(os.path.join(K, "macro_daily.csv"), parse_dates=["date"]).sort_values("date")
    Mc["vix_term"] = Mc.vix / Mc.vix3m
    mac = Mc[["date", "vix_chg", "vix_term", "us10y_chg_bp", "dxy_ret", "nq_vs_es"]].rename(columns={"date": "mdate"})
    T = pd.merge_asof(T.sort_values("date"), mac, left_on="date", right_on="mdate", allow_exact_matches=False)  # PRIOR close
    E = pd.read_csv(os.path.join(K, "data", "econ_events_red.csv"))
    E = E[E.event != "event"]; ts = pd.to_datetime(E.release_ts_utc, errors="coerce", utc=True).dt.tz_convert("America/Chicago")
    E = E.assign(ct=ts).dropna(subset=["ct"])
    E = E[E.get("is_scheduled", "false").astype(str).str.lower().ne("x")]
    mins = E.ct.dt.hour * 60 + E.ct.dt.minute
    pre_days = set(E.ct[(mins >= 7 * 60) & (mins < 8 * 60 + 30) & (E.event != "fomc")].dt.date)
    fomc_days = set(E.ct[E.event == "fomc"].dt.date)
    T["red_pre"] = T.date.dt.date.isin(pre_days).astype(int); T["fomc"] = T.date.dt.date.isin(fomc_days).astype(int)
    T = T[T.ok & np.isfinite(T.rth_ret) & np.isfinite(T.on_ret)].reset_index(drop=True)
    return T


def band_checks():
    """bias.py rules on the RTH grid: hourly 09..14 CT, band = 1.2 x mean |c/o-1| at that minute over the last 14 sessions."""
    D = om.days(); dates = pd.to_datetime(D["dates"]); O, C = D["o"], D["c"]; ok = D["have"] > 900
    rows = []
    rth = [i for i in range(len(dates)) if ok[i]]
    for j, i in enumerate(rth):
        if j < 14: continue
        hist = rth[j - 14:j]; o = float(O[i, O830]); close = float(C[i, C1459])
        for h in (9, 10, 11, 12, 13, 14):
            t = M(h, 0) - 1
            sig = float(np.mean([abs(C[k, t] / O[k, O830] - 1) for k in hist])); c = float(C[i, t])
            b = 1 if c > o * (1 + 1.2 * sig) else -1 if c < o * (1 - 1.2 * sig) else 0
            rows.append((dates[i], h, b, np.sign(close - c)))
    return pd.DataFrame(rows, columns=["date", "h", "band", "rest"])


def day_perm_p(x, y, B=20000, seed=1):
    """two-sided p of corr(x, y) with day-level permutation (days are the unit; one row per day)."""
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    x = (x - x.mean()) / (x.std() + 1e-12); r = float(np.mean(x * (y - y.mean())) / (y.std() + 1e-12))
    rng = np.random.default_rng(seed); ys = (y - y.mean()) / (y.std() + 1e-12)
    null = np.array([np.mean(x * rng.permutation(ys)) for _ in range(B)])
    return r, float((np.abs(null) >= abs(r)).mean() + 1 / B), int(m.sum())


def analyse(T, Bc, lo, hi):
    t = T[(T.date >= lo) & (T.date <= hi)]; out = {"period": [lo, hi], "days": int(len(t)), "T1_direction": {}, "T2_size": {}}
    up = float((t.rth_ret > 0).mean()); out["base_up_rate"] = round(up, 3)
    for f in FEATS:
        x = t[f].to_numpy(float)
        r, p, n = day_perm_p(x, t.rth_ret.to_numpy(float), B=5000)
        q = pd.qcut(pd.Series(x).rank(method="first"), 5, labels=False) if len(np.unique(x[np.isfinite(x)])) > 5 else pd.Series(x)
        byq = t.assign(q=q.values).groupby("q").rth_ret.agg(lambda s: round(float((s > 0).mean()), 3)).to_dict()
        out["T1_direction"][f] = {"corr": round(r, 4), "p": round(p, 4), "n": n, "up_rate_by_bucket": {str(k): v for k, v in byq.items()}}
        r2, p2, _ = day_perm_p(np.abs(x) if f.endswith("ret") else x, t.size_z.to_numpy(float), B=5000)
        out["T2_size"][f] = {"corr": round(r2, 4), "p": round(p2, 4)}
    b = Bc[(Bc.date >= lo) & (Bc.date <= hi) & (Bc.band != 0)].merge(t[["date", "on_ret"]], on="date")
    b["hit"] = (b.band == b.rest).astype(int); b["agree"] = np.sign(b.on_ret) == b.band
    g = b.groupby("agree").hit.agg(["mean", "size"])
    # day-level test: per day mean hit, compare agree vs disagree days by permutation of the agree label within checks' days
    dd = b.groupby(["date", "agree"]).hit.mean().reset_index()
    a, d_ = dd[dd.agree].hit.to_numpy(), dd[~dd.agree].hit.to_numpy(); diff = a.mean() - d_.mean()
    rng = np.random.default_rng(3); allv = np.r_[a, d_]; k = len(a)
    null = np.array([(lambda p_: p_[:k].mean() - p_[k:].mean())(rng.permutation(allv)) for _ in range(5000)])
    out["T3_band"] = {"hit_rate_all": round(float(b.hit.mean()), 3), "checks": int(len(b)),
                      "hit_when_overnight_agrees": round(float(g.loc[True, "mean"]), 3), "n_agree": int(g.loc[True, "size"]),
                      "hit_when_overnight_disagrees": round(float(g.loc[False, "mean"]), 3), "n_disagree": int(g.loc[False, "size"]),
                      "diff": round(float(diff), 3), "p": round(float((np.abs(null) >= abs(diff)).mean() + 1 / 5000), 4)}
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "design"
    T = table(); Bc = band_checks()
    lo, hi = ("2014-01-01", "2021-12-31") if mode == "design" else ("2022-01-01", "2099-12-31")
    res = analyse(T, Bc, lo, hi); os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, f"overnight_{mode}.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("T1_direction", "T2_size")}, indent=1))
    for f, v in res["T1_direction"].items():
        print(f"{f:13s} dir corr {v['corr']:+.4f} p {v['p']:.4f} | size corr {res['T2_size'][f]['corr']:+.4f} p {res['T2_size'][f]['p']:.4f}")


def holdout_composite(T, Bc):
    """frozen decision (knowledge/research_out/overnight_decision.json): z-weights from the DESIGN period only."""
    dec = json.load(open(os.path.join(OUT, "overnight_decision.json")))["direction_candidates_design_p_lt_0.01"]
    d = T[(T.date >= "2014-01-01") & (T.date <= "2021-12-31")]; h = T[T.date >= "2022-01-01"].copy()
    mu = {f: d[f].mean() for f in dec}; sd = {f: d[f].std() for f in dec}
    sc = lambda X: sum(s * (X[f] - mu[f]) / sd[f] for f, s in dec.items())
    ds = sc(d); q20, q80 = np.nanpercentile(ds, 20), np.nanpercentile(ds, 80)
    h["score"] = sc(h); r, p, n = day_perm_p(h.score, h.rth_ret, B=20000)
    top, bot = h[h.score >= q80], h[h.score <= q20]
    rs, ps, _ = day_perm_p(h.on_range_z, h.size_z, B=20000)
    b = Bc[(Bc.date >= "2022-01-01") & (Bc.band != 0)].merge(h[["date", "score", "on_ret"]], on="date")
    b["hit"] = (b.band == b.rest).astype(int); b["agree"] = np.sign(b.score) == b.band
    dd = b.groupby(["date", "agree"]).hit.mean().reset_index(); a, x = dd[dd.agree].hit.to_numpy(), dd[~dd.agree].hit.to_numpy()
    rng = np.random.default_rng(5); allv = np.r_[a, x]; k = len(a); diff = a.mean() - x.mean()
    null = np.array([(lambda p_: p_[:k].mean() - p_[k:].mean())(rng.permutation(allv)) for _ in range(5000)])
    hb = h.assign(zq=pd.qcut(h.on_range_z.rank(method="first"), 5, labels=False)).groupby("zq").size_z.median().round(2).to_dict()
    return {"direction_composite": {"corr": round(r, 4), "p": round(p, 4), "n": n, "base_up": round(float((h.rth_ret > 0).mean()), 3),
                                    "up_rate_top20": round(float((top.rth_ret > 0).mean()), 3), "n_top": int(len(top)),
                                    "up_rate_bottom20": round(float((bot.rth_ret > 0).mean()), 3), "n_bottom": int(len(bot)),
                                    "mean_ret_top_bp": round(float(top.rth_ret.mean() * 1e4), 1), "mean_ret_bottom_bp": round(float(bot.rth_ret.mean() * 1e4), 1)},
            "size_on_range_z": {"corr": round(rs, 4), "p": round(ps, 4), "median_size_by_quintile": {str(k_): v for k_, v in hb.items()}},
            "band_x_composite": {"hit_agree": round(float(b[b.agree].hit.mean()), 3), "n_agree": int(b.agree.sum()),
                                 "hit_disagree": round(float(b[~b.agree].hit.mean()), 3), "n_disagree": int((~b.agree).sum()),
                                 "diff": round(float(diff), 3), "p": round(float((np.abs(null) >= abs(diff)).mean() + 1 / 5000), 4)}}


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "holdout":
    res2 = holdout_composite(T, Bc)
    json.dump(res2, open(os.path.join(OUT, "overnight_holdout_composite.json"), "w"), indent=1); print(json.dumps(res2, indent=1))
