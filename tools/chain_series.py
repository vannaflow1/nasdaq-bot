"""tools/chain_series.py - intraday option mid-price series from the chain snapshots (wish #41, 15 Nov 2026).
tools/chain_snap.py (wish #23) stores one CBOE delayed chain per snapshot under knowledge/data/chains/<SYM>/<day>/<HHMM>.csv.gz.
This turns those snapshots into tidy time series for research:
  load(sym, start=None, end=None)   -> long table: one row per (quote_ts, contract) with mid, spread, rel_spread, moneyness
  atm_series(sym, ...)              -> one row per snapshot: spot, 0-DTE ATM call/put/straddle mid, ATM IV, spread
  coverage(sym)                     -> per day: snapshots, first/last quote time, median / max gap in minutes
Time axis = CBOE's own quote timestamp ('quote_ts'; observed to be UTC: the 09:59 NY fetch carries 14:59:16), never the
fetch time (no lookahead from fetch lag).
Mid is only computed for sane quotes (bid > 0, ask >= bid); otherwise NaN. Snapshots sharing a quote_ts are de-duplicated.
Honest limit: GitHub's 5-minute cron is heavily throttled - the first two weeks have ~5-8 snapshots per day (~50 min apart),
so this is an intraday series, not yet a true 5-minute one. coverage() reports the real cadence; never assume 5 minutes.
Research side only. Usage: python tools/chain_series.py [SYM]   (prints coverage + ATM series summary)"""
import glob, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(HERE, "knowledge", "data", "chains")


def _files(sym, start=None, end=None):
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, sym, "*", "*.csv.gz"))):
        if p.endswith("_surface.csv.gz"): continue
        day = os.path.basename(os.path.dirname(p))
        if (start and day < str(start)) or (end and day > str(end)): continue
        out.append(p)
    return out


def load(sym="QQQ", start=None, end=None):
    """Long table of every saved contract quote; one row per (quote_ts, expiration, cp, strike)."""
    parts = []
    for p in _files(sym, start, end):
        try: d = pd.read_csv(p)
        except Exception: continue                            # a truncated file never stops the series
        if d.empty: continue
        d["file"] = os.path.relpath(p, ROOT); parts.append(d)
    if not parts: return pd.DataFrame()
    d = pd.concat(parts, ignore_index=True)
    d["quote_ts"] = pd.to_datetime(d["quote_ts"], errors="coerce")
    d = d[d.quote_ts.notna()]
    ok = (d.bid > 0) & (d.ask >= d.bid)
    d["mid"] = np.where(ok, (d.bid + d.ask) / 2, np.nan)
    d["spread"] = np.where(ok, d.ask - d.bid, np.nan)
    d["rel_spread"] = d["spread"] / d["mid"]
    d["moneyness"] = d.strike / d.spot - 1
    d = d.sort_values(["quote_ts", "expiration", "strike", "cp", "file"])
    d = d.drop_duplicates(["quote_ts", "expiration", "cp", "strike"], keep="first")   # same CBOE quote fetched twice
    return d.reset_index(drop=True)


def atm_series(sym="QQQ", start=None, end=None, d=None):
    """One row per snapshot: nearest-expiry (0-DTE on expiry days) ATM call / put / straddle mid at the strike nearest spot."""
    d = load(sym, start, end) if d is None else d
    if d.empty: return pd.DataFrame()
    rows = []
    for ts, g in d.groupby("quote_ts"):
        g = g[g.expiration == g.expiration.min()]
        k = g.strike.iloc[(g.strike - g.spot).abs().argsort().iloc[0]]
        c, p = g[(g.strike == k) & (g.cp == "C")], g[(g.strike == k) & (g.cp == "P")]
        cm = float(c.mid.iloc[0]) if len(c) else np.nan; pm = float(p.mid.iloc[0]) if len(p) else np.nan
        rows.append({"quote_ts": ts, "spot": float(g.spot.iloc[0]), "expiration": g.expiration.iloc[0],
                     "dte": int(g.dte.iloc[0]), "atm_strike": k, "call_mid": cm, "put_mid": pm, "straddle_mid": cm + pm,
                     "atm_iv": float(pd.concat([c.iv, p.iv]).mean()) if len(c) + len(p) else np.nan,
                     "straddle_spread": float(c.spread.sum() + p.spread.sum()) if len(c) and len(p) else np.nan})
    return pd.DataFrame(rows)


def coverage(sym="QQQ", d=None):
    """Per day: number of distinct quote times, first / last quote time, median and max gap (minutes)."""
    d = load(sym) if d is None else d
    if d.empty: return pd.DataFrame()
    t = pd.Series(sorted(d.quote_ts.unique())); t = pd.to_datetime(t)
    rows = []
    for day, g in t.groupby(t.dt.date):
        gaps = g.diff().dt.total_seconds().dropna() / 60
        rows.append({"day": str(day), "snapshots": len(g), "first": g.iloc[0].strftime("%H:%M"),
                     "last": g.iloc[-1].strftime("%H:%M"),
                     "median_gap_min": round(float(gaps.median()), 1) if len(gaps) else np.nan,
                     "max_gap_min": round(float(gaps.max()), 1) if len(gaps) else np.nan})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    d = load(sym)
    if d.empty: print(f"no {sym} snapshots under {ROOT}"); sys.exit(0)
    print(f"{sym}: {len(d)} contract quotes, {d.quote_ts.nunique()} snapshots, "
          f"{d.quote_ts.dt.date.nunique()} days, mid valid {d.mid.notna().mean():.0%}")
    print(coverage(sym, d).to_string(index=False))
    a = atm_series(sym, d=d)
    print(a.tail(8).to_string(index=False))
