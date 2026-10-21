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


def load_proxy(mk, lo, hi):
    """Fetch [lo - warm-up, hi] from the proxy feed and install it in memory as market '<mk>_SEALED'.
    Returns (market name, session indices inside [lo, hi])."""
    import strategy_lab as S
    from tools import dukascopy as DK
    d0 = date.fromisoformat(lo) - timedelta(WARMUP_DAYS); d1 = date.fromisoformat(hi)
    n = DK.fetch(mk, d0, d1)
    miss = [d for m, d in DK.MISSING if m == mk and lo <= d <= hi]
    if not len(n) or len(miss) > 5: raise RuntimeError(f"proxy data for {mk} incomplete ({len(miss)} weekdays missing) - try again later")
    A, M = DK.sessions(n)
    name = f"{mk}_SEALED"; S.install_market(name, A, M, like=mk)
    idx = np.where((M.session >= lo) & (M.session <= hi))[0]
    return name, idx


def proxy_trades(S, X, sleeve, lo=None, hi=None, window=None):
    """Trades of a frozen sleeve on the proxy feed: the sealed window (default) or [lo, hi] per market."""
    rows = []
    for sp in sleeve:
        mk = (sp.get("market") or "NQ").upper(); a, b = window or SEALED[mk]
        a = lo or a; b = hi or b
        name, idx = load_proxy(mk, a, b)
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


def alpha_v2(j, alpha=ALPHA_SEQ):
    """Families registered under the v2 rules: the j-th family scored gets alpha * 6 / (pi^2 j^2) - the sequence sums to
    alpha in total (the old alpha/k rule summed to ~0.13 after 7 families; those verdicts stand, the old rule is retired)."""
    return float(alpha * 6 / (np.pi ** 2 * j * j))


if __name__ == "__main__":
    print("OBF boundaries:", obf_bounds())
    for j in range(1, 6): print("alpha_v2", j, round(alpha_v2(j), 5))
