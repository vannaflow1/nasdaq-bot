"""sealed.py - the new exam design (expert review 2, 21 Oct 2026).

THE 2024-NOW EXAM IS SPENT: F1, F2, prop-search and the recent track have all used it, and the nightly session that
registers families has seen those outcomes. From now on:
  1. SEALED WINDOW. Volta's own futures data stops before these dates, so they have never been seen:
       NQ (and ES/YM/RTY) 2026-02-02 .. 2026-10-09 | GC 2026-06-29 .. 2026-10-09 | CL 2026-06-22 .. 2026-10-09
     The bars come from Dukascopy's free CFD feed (tools/dukascopy.py), fetched ONLY inside the exam job on GitHub,
     kept in memory and thrown away. They are never written to the repo, so search, family scoring, the self-check, the
     Gemini agent and Claude sessions cannot see them (this sandbox cannot even reach the feed).
     The ~45 days before a window are fetched as warm-up for look-back features only (bands, ATR) - never scored.
  2. ONE SHOT PER FAMILY, POWER-GATED. A family's exam is spent only if the exam has >= 70% power for the family's SHRUNK
     validation edge (half its validation median). Otherwise the family goes to the forward route instead of wasting it.
  3. FORWARD ROUTE (group-sequential). Every day after a family's freeze date counts. Checks at 10 equally spaced
     information points up to N_MAX trades, O'Brien-Fleming boundaries (one-sided alpha 0.05 overall), non-binding
     futility stop (z < 0 after half the information).
  4. Evidence is counted in DAYS: every day's trades (all markets) are summed into one daily R before any test, and the
     uncertainty comes from a stationary block bootstrap over days (mean block 5) - honest about same-day correlation.
  5. 2024-now is demoted to validation for families registered after 21 Oct 2026."""
import json, os, sys
from datetime import date, datetime, timedelta, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
SEALED = {"NQ": ("2026-02-02", "2026-10-09"), "ES": ("2026-02-02", "2026-10-09"), "YM": ("2026-02-02", "2026-10-09"),
          "RTY": ("2026-02-02", "2026-10-09"), "GC": ("2026-06-29", "2026-10-09"), "CL": ("2026-06-22", "2026-10-09")}
POWER_GATE, N_MAX, LOOKS, ALPHA_SEQ = 0.70, 3000, 10, 0.05
WARMUP_DAYS = 45


def edge_days(T, B=2000, block=5, seed=0):
    """Per-trade edge with day-level uncertainty. T: trades with session, R (any markets)."""
    if not len(T): return {"n": 0, "days": 0, "edge": np.nan, "se": np.nan, "z": np.nan, "edge_lb10": np.nan, "sd_day": np.nan}
    g = T.groupby("session").R.agg(["sum", "count"]).sort_index(); s, c = g["sum"].to_numpy(), g["count"].to_numpy()
    nd = len(g); edge = s.sum() / c.sum(); rng = np.random.default_rng(seed); reps = np.empty(B)
    p = 1.0 / block
    for b in range(B):                                        # stationary block bootstrap over days
        idx = np.empty(nd, int); i = rng.integers(nd)
        for t in range(nd):
            if t and rng.random() < p: i = rng.integers(nd)
            idx[t] = i; i = (i + 1) % nd
        reps[b] = s[idx].sum() / max(c[idx].sum(), 1)
    se = float(reps.std(ddof=1))
    return {"n": int(c.sum()), "days": int(nd), "edge": float(edge), "se": se, "z": float(edge / se) if se > 0 else np.nan,
            "edge_lb10": float(np.quantile(reps, 0.10)), "sd_day": float(np.std(s - edge * c, ddof=1)),
            "trades_per_day": float(c.mean())}


def exam_power(true_edge, se_exam, z_crit=1.2816):
    """P(exam's 90% lower bound > 0) if the true edge is true_edge."""
    from statistics import NormalDist
    if not (se_exam and np.isfinite(se_exam) and se_exam > 0): return 0.0
    return float(NormalDist().cdf(true_edge / se_exam - z_crit))


def expected_exam_se(val, val_days_per_market, markets):
    """Scale the validation SE to the sealed window's trading days (same trade rate, same per-day noise)."""
    sealed_days = sum(np.busday_count(SEALED[m][0], SEALED[m][1]) * 0.96 for m in markets)   # ~4% holidays / gaps
    vd = sum(val_days_per_market.get(m, 0) for m in markets)
    if not vd or not np.isfinite(val.get("se", np.nan)): return np.nan, 0
    return float(val["se"] * np.sqrt(vd / max(sealed_days, 1))), int(sealed_days)


def load_proxy(mk, lo, hi, X=None):
    """Fetch [lo - warm-up, hi] from the proxy feed and install it in memory as market '<mk>_SEALED'.
    Returns (market name, session indices inside [lo, hi]). NQ sessions get the validated stop input (match_futures_inputs);
    where it does not exist (brain memory has no Feb-Oct 2026 rows) they cannot trade until a substitute is calibrated."""
    import strategy_lab as S
    from tools import dukascopy as DK
    d0 = date.fromisoformat(lo) - timedelta(WARMUP_DAYS); d1 = date.fromisoformat(hi)
    n = DK.fetch(mk, d0, d1)
    miss = [d for m, d in DK.MISSING if m == mk and lo <= d <= hi]
    if not len(n) or len(miss) > 5: raise RuntimeError(f"proxy data for {mk} incomplete ({len(miss)} weekdays missing) - try again later")
    A, M = DK.sessions(n)
    M = match_futures_inputs(M, mk, X)
    name = f"{mk}_SEALED"; S.install_market(name, A, M, like=mk)
    idx = np.where((M.session >= lo) & (M.session <= hi))[0]
    return name, idx


def nq_fc_frac(sessions, X):
    """NQ's stop input, the same one every NQ futures backtest and validation used: strat_sessions.fc_frac == exp(l_bot), the
    brain's evening forecast for that session (checked 22 Oct 2026: corr 1.0000, ratio 0.9999). dukascopy.sessions puts a
    20-session REALIZED range there instead - 1.64x larger on NQ: F2/F10 traded on it are a different strategy (on identical
    futures prices it alone gives daily-R corr 0.68 vs the validated rule - the whole 'NQ proxy failure'). Source: brain
    memory (memory date + gap_days = the session), then brain_preds.csv (next_date = the session). A session without the
    forecast gets NaN: no trade, never a different stop rule (knowledge/frozen/F10_forward_inputs.json)."""
    import math
    out = {}
    if X is not None and "l_bot" in X and "gap_days" in X:
        for d, lb, gd in zip(X.index, X["l_bot"].to_numpy(float), X["gap_days"].fillna(1).to_numpy(float)):
            if np.isfinite(lb): out[(pd.Timestamp(d) + pd.Timedelta(days=int(gd))).strftime("%Y-%m-%d")] = math.exp(lb)
    fp = os.path.join(os.path.dirname(K), "brain_preds.csv")
    if os.path.exists(fp):
        P = pd.read_csv(fp)
        for nd, f in zip(P["next_date"].astype(str).str[:10], P["feat"]):
            try: out.setdefault(nd, math.exp(float(json.loads(f)["l_bot"])))
            except Exception: pass
    return np.array([out.get(str(s)[:10], np.nan) for s in sessions], float)


SUB_COLS = ["l_vix9d", "l_vix", "l_vix3m", "l_vvix", "r1", "r5", "r20"]


def _sub_features(rng_frac, mem_dates):
    """Inputs that exist for EVERY day (macro_daily.csv: VIX family; the market's own past RTH ranges)."""
    mac = pd.read_csv(os.path.join(K, "macro_daily.csv"), parse_dates=["date"]).set_index("date")
    r = pd.Series(np.asarray(rng_frac, float))
    F = pd.DataFrame({"r1": np.log(r.shift(1)), "r5": np.log(r.shift(1).rolling(5).mean()), "r20": np.log(r.shift(1).rolling(20).mean())})
    d = pd.to_datetime(pd.Series(mem_dates), errors="coerce")
    for c in ("vix9d", "vix", "vix3m", "vvix"): F["l_" + c] = np.log(mac[c].reindex(d).to_numpy())
    return F[SUB_COLS].replace([np.inf, -np.inf], np.nan)


def fit_nq_fc_substitute():
    """A stand-in for exp(l_bot) where the brain memory has a gap (Dec 2025 - Oct 2026): OLS of l_bot on the VIX family and
    NQ's past ranges, fitted on every seen NQ futures session (input replication only - never chosen by any strategy's R).
    Expert review 4 measured the 2014-21 fit on 2022-now: R^2 0.775, typical error 14%, F10 v43 daily-R corr 0.898.
    NOT used by any frozen test unless an addendum in knowledge/frozen/ says so."""
    import strategy_lab as S
    D = S.data("NQ"); M = D["M"]
    rng = (np.nanmax(D["H"], 1) - np.nanmin(D["L"], 1)) / D["O"][:, 0]
    F = _sub_features(rng, M.date.values); y = np.log(M.fc_frac.to_numpy(float))
    ok = np.isfinite(F.values).all(1) & np.isfinite(y)
    A = np.c_[np.ones(ok.sum()), F.values[ok]]; b = np.linalg.lstsq(A, y[ok], rcond=None)[0]; res = y[ok] - A @ b
    out = {"cols": SUB_COLS, "coef": [float(x) for x in b], "fit_rows": int(ok.sum()), "resid_sd_log": round(float(res.std()), 4),
           "fit_window": [str(M.session[ok].min()), str(M.session[ok].max())]}
    os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
    json.dump(out, open(os.path.join(K, "research_out", "nq_fc_substitute.json"), "w"), indent=1)
    return out


def substitute_fc(A, M, fit):
    """The substitute stop input for sessions M with bars A (the proxy's own past ranges + the VIX family)."""
    rng = (np.nanmax(A["H"], 1) - np.nanmin(A["L"], 1)) / A["O"][:, 0]
    F = _sub_features(rng, M.date.values)
    return np.exp(np.c_[np.ones(len(F)), F.values] @ np.asarray(fit["coef"], float))


def match_futures_inputs(M, mk, X):
    """Give proxy / archive sessions the inputs the futures backtest used (NQ: the brain's stop forecast)."""
    if (mk or "NQ").upper() == "NQ":
        M = M.copy(); M["fc_frac"] = nq_fc_frac(M.session, X)
    return M


def proxy_trades(S, X, sleeve, lo=None, hi=None, window=None):
    """Trades of a frozen sleeve on the proxy feed: the sealed window (default) or [lo, hi] per market."""
    rows = []
    for sp in sleeve:
        mk = (sp.get("market") or "NQ").upper(); a, b = window or SEALED[mk]
        a = lo or a; b = hi or b
        name, idx = load_proxy(mk, a, b, X)
        T = S.backtest(dict(sp, market=name), X, idx)
        if len(T): rows.append(T.assign(market=mk, spec=json.dumps(sp)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["session", "i", "pnl", "R", "side", "k", "market", "spec"])


def archive_trades(S, X, sleeve, lo, hi):
    """Trades of a frozen sleeve on REAL futures bars from the nightly archive (tools/bar_archive.py, Yahoo, Chicago time),
    for forward days lo..hi. Look-back features (noise bands, ATR, expected range) need ~45 days of history before the
    archive starts: those come from the proxy feed (only to compute bands - no warm-up day is ever scored)."""
    import glob
    from tools import dukascopy as DK
    rows = []
    for sp in sleeve:
        mk = (sp.get("market") or "NQ").upper()
        fs = sorted(glob.glob(os.path.join(K, "data", "archive", f"{mk}_*.csv.gz")))
        if not fs: continue
        a = pd.concat([pd.read_csv(f, parse_dates=["ts"]) for f in fs]).drop_duplicates("ts").sort_values("ts")
        a = a.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"}); a["sym"] = mk
        start = a.ts.min().normalize() + pd.Timedelta(days=1)   # first full archive day
        a = a[a.ts >= start - pd.Timedelta(hours=7)]            # from 17:00 CT the evening before
        w = DK.fetch(mk, (start - pd.Timedelta(days=WARMUP_DAYS)).date(), (start - pd.Timedelta(days=1)).date())
        w = w[w.ts < a.ts.min()] if len(w) else w
        n = pd.concat([w[["ts", "o", "h", "l", "c", "v", "sym"]], a[["ts", "o", "h", "l", "c", "v", "sym"]]], ignore_index=True) if len(w) else a
        A, M = DK.sessions(n)
        if A is None: continue
        M = match_futures_inputs(M, mk, X)                    # 22 Oct 2026: the validated stop input, not a realized range
        name = f"{mk}_FWD"; S.install_market(name, A, M, like=mk)
        lo2 = max(lo, start.strftime("%Y-%m-%d"))
        idx = np.where((M.session >= lo2) & (M.session <= hi))[0]
        if not len(idx): continue
        miss = [s for s in M.session.values[idx] if not np.isfinite(M.fc_frac.values[M.session.values == s][0])]
        if miss: print(f"WARNING {mk}: no stop forecast for forward session(s) {miss[:5]} - no trade there (not a different rule)")
        T = S.backtest(dict(sp, market=name), X, idx)
        if len(T): rows.append(T.assign(market=mk, spec=json.dumps(sp)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["session", "i", "pnl", "R", "side", "k", "market", "spec"])


def obf_bounds(looks=LOOKS, alpha=ALPHA_SEQ, sims=200000, seed=11):
    """O'Brien-Fleming boundaries z_k = C * sqrt(looks / k) with P(cross any | no edge) = alpha (Monte Carlo, fixed seed)."""
    rng = np.random.default_rng(seed)
    inc = rng.standard_normal((sims, looks)); W = np.cumsum(inc, 1); Z = W / np.sqrt(np.arange(1, looks + 1))
    w = np.sqrt(looks / np.arange(1, looks + 1)); lo, hi = 1.0, 4.0
    for _ in range(40):
        c = (lo + hi) / 2; p = (Z >= c * w).any(1).mean()
        lo, hi = (c, hi) if p > alpha else (lo, c)
    return [round(float(c * x), 3) for x in w]


def forward_decision(Tf, n_max=N_MAX, looks=LOOKS):
    """Group-sequential verdict on forward trades Tf (session, R) - one check per crossed information point."""
    st = edge_days(Tf, B=1000)
    if st["n"] == 0: return "WAITING", st
    k = min(looks, int(st["n"] / (n_max / looks)))            # information looks completed
    st["look"] = k; st["bounds"] = obf_bounds(looks)
    if k == 0: return "WAITING", st
    zb = st["bounds"][k - 1]; st["boundary"] = zb
    if st["z"] >= zb: return "CONFIRMED", st
    if k >= looks / 2 and st["z"] < 0: return "STOPPED (futility)", st
    if k >= looks: return "NOT CONFIRMED", st
    return "CONTINUE", st


def alpha_fast(j):
    """Fast-track epoch (owner OK 24 Oct 2026, knowledge/frozen/epoch_fast.json): 5 fixed slots of 0.01, then 0."""
    try: return float(json.load(open(os.path.join(K, "frozen", "epoch_fast.json")))["budget"]["slots"].get(str(j), 0.0))
    except Exception: return 0.0


def alpha_v2(j, alpha=ALPHA_SEQ):
    """Expert review 3: j = 1..3 used the sequence (F8, F9, F10); the remaining 0.0086 is split into FIXED slots declared in
    knowledge/frozen/alpha_slots.json (j = 4: 0.0040, 5 and 6: 0.0023); after that 0 - no more families."""
    if j >= 4:
        try: return float(json.load(open(os.path.join(K, "frozen", "alpha_slots.json")))["slots"].get(str(j), 0.0))
        except Exception: return 0.0
    return _alpha_seq(j, alpha)


def _alpha_seq(j, alpha=ALPHA_SEQ):
    """Families registered under the v2 rules: the j-th family scored gets alpha * 6 / (pi^2 j^2) - the sequence sums to
    alpha in total (the old alpha/k rule summed to ~0.13 after 7 families; those verdicts stand, the old rule is retired)."""
    return float(alpha * 6 / (np.pi ** 2 * j * j))


if __name__ == "__main__":
    print("OBF boundaries:", obf_bounds())
    for j in range(1, 6): print("alpha_v2", j, round(alpha_v2(j), 5))


def forward_decision_v3(Tf, design):
    """Futility-first forward test (expert review 3), frozen in knowledge/frozen/<family>_forward_design.json:
    futility looks at 100/200/300 trades (conditional power for +0.08R < 10% or posterior P(edge > 0) < 0.2, each judged on
    exactly the first L trades), CUSUM kill on daily R, O'Brien-Fleming efficacy backstop up to N_MAX = 600."""
    from statistics import NormalDist
    N = NormalDist(); d = design; out = {"n": int(len(Tf))}
    if not len(Tf): return "WAITING", out
    Tf = Tf.sort_values(["session", "k"]).reset_index(drop=True); R = Tf.R.to_numpy(float)
    pv = d["posterior"]; vv = (pv["validation"]["se"] ** 2) / pv["validation"]["weight"]
    def posterior(r):
        sd = max(float(np.std(r, ddof=1)) if len(r) > 2 else 2.0, 1.5); prec_f = len(r) / sd ** 2
        prec = 1 / 0.05 ** 2 + 1 / vv + prec_f; mu = (pv["validation"]["edge"] / vv + (r.mean() if len(r) else 0) * prec_f) / prec
        return mu, prec ** -0.5, 1 - N.cdf(-mu * prec ** 0.5)
    ef = d["efficacy"]; nmax = ef["n_max"]; bounds = obf_bounds(ef["looks"], ef["alpha_one_sided"])
    fu = d["futility"]; sd_cp = fu["cp_sd_per_trade_R"]; delta = fu["cp_alternative_edge_R"]
    def cond_power(r):
        n = len(r); m = max(nmax - n, 1); b = bounds[-1]
        return 1 - N.cdf((b * sd_cp * np.sqrt(nmax) - r.sum() - delta * m) / (sd_cp * np.sqrt(m)))
    mu, sdp, p_pos = posterior(R); out.update(edge=float(R.mean()), posterior_mean=round(mu, 4), posterior_sd=round(sdp, 4),
                                              p_edge_pos=round(p_pos, 3), cond_power=round(cond_power(R), 3))
    for L in fu["looks_trades"]:                                  # futility, judged on exactly the first L trades
        if len(R) >= L:
            r = R[:L]; cp = cond_power(r); pp = posterior(r)[2]
            out[f"look_{L}"] = {"cond_power": round(cp, 3), "p_edge_pos": round(pp, 3)}
            if cp < fu["stop_if_conditional_power_below"] or pp < fu["stop_if_posterior_p_edge_pos_below"]:
                return "STOPPED (futility)", out
    cu = d["cusum_kill"]; dayR = Tf.groupby("session").R.sum().to_numpy(); C = 0.0; cmax = 0.0
    for x in dayR:
        C = max(0.0, C + (cu["k"] - x)); cmax = max(cmax, C)
        if C > cu["h"]: out["cusum"] = round(C, 2); return "STOPPED (CUSUM kill)", out
    out["cusum"] = round(C, 2)
    st = edge_days(Tf, B=1000); k = min(ef["looks"], int(len(R) / (nmax / ef["looks"])))
    out.update(z=st["z"], look=k)
    if k >= 1:
        out["boundary"] = bounds[k - 1]
        if st["z"] >= bounds[k - 1]: return "CONFIRMED", out
        if k >= ef["looks"]: return "NOT CONFIRMED", out
    return "CONTINUE", out
