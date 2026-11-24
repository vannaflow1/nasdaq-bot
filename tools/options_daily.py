"""tools/options_daily.py - turns a free 18-year daily options history into one small table per symbol (Volta wish #28).

Source (found 24 Nov 2026): github.com/philippdubach/options-data - daily end-of-day option chains for 104 US
tickers, 2 Jan 2008 to 16 Dec 2025, hosted free on Cloudflare R2, "for educational and research purposes". The raw
files are big (QQQ 384 MB) and never go into the repo. This script downloads one symbol, boils every trading day
down to a handful of numbers, and writes knowledge/data/options_daily/<SYM>_daily.csv (a few hundred kB).

Columns (one row per trading day; everything uses only that day's chain, nothing looks ahead):
  spot            underlying close
  gex_norm        dealer gamma, same formula as qqq_gex_daily.gexn (calls +, puts -, per unit of open interest)
  gex_rank_252    where gex_norm sits among the previous 252 days (0 = lowest, 1 = highest; NaN for the first year)
  oi_calls, oi_puts, vol_calls, vol_puts
  atm_iv_front    ATM implied vol of the nearest expiry with 1+ days left
  atm_iv_30       ATM implied vol interpolated to 30 days
  term_ratio      atm_iv_front / atm_iv_30 (above 1 = front end bid)
  skew25_30       25-delta put IV minus 25-delta call IV, expiry nearest 30 days
  n_contracts     rows that day (data-quality check)

PLAIN-WORDS RULE: this only builds the table. Nothing here relates it to NQ prices or tests a strategy - that would
spend an alpha slot and needs the owner's OK (knowledge/proposals/).
Run: python tools/options_daily.py QQQ        (in the options-daily workflow; needs pyarrow + internet)"""
import os, sys, urllib.request
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "knowledge", "data", "options_daily")
BASE = "https://static.philippdubach.com/data/options/{}/{}.parquet"
COLS = ["date", "expiration", "strike", "type", "volume", "open_interest", "implied_volatility", "delta", "gamma"]


def _nearest(x, col, target):
    return x.iloc[(x[col] - target).abs().argsort()[:1]]


def atm_iv(e, spot):
    """Mean call/put IV at the strike nearest spot for one expiry, or NaN."""
    e = e[e.implied_volatility > 0]
    if e.empty: return np.nan
    k = e.strike.iloc[(e.strike - spot).abs().argsort().iloc[0]]
    v = e[e.strike == k].implied_volatility
    return float(v.mean()) if len(v) else np.nan


def day_row(d, spot):
    """Summary numbers for one trading day's chain (DataFrame with COLS + dte, is_call)."""
    r = {"spot": spot, "n_contracts": len(d)}
    c, p = d[d.is_call], d[~d.is_call]
    r.update(oi_calls=float(c.open_interest.sum()), oi_puts=float(p.open_interest.sum()),
             vol_calls=float(c.volume.sum()), vol_puts=float(p.volume.sum()))
    g = d[(d.open_interest > 0) & (d.dte >= 0) & np.isfinite(d.gamma)]
    tot = g.open_interest.sum()
    if tot > 0 and spot > 0:
        sign = np.where(g.is_call, 1.0, -1.0)
        r["gex_norm"] = float((sign * g.gamma * g.open_interest * 100 * spot * spot * 0.01).sum() / (tot * 100 * spot) * 1e4)
    else:
        r["gex_norm"] = np.nan
    exps = sorted(d.loc[d.dte >= 1, "dte"].unique())
    ivs = {t: atm_iv(d[d.dte == t], spot) for t in exps}
    ivs = {t: v for t, v in ivs.items() if np.isfinite(v)}
    r["atm_iv_front"] = ivs[min(ivs)] if ivs else np.nan
    if ivs:
        ts = np.array(sorted(ivs)); vs = np.array([ivs[t] for t in ts])
        r["atm_iv_30"] = float(np.interp(30, ts, vs)) if ts.min() <= 30 <= ts.max() else (float(vs[0]) if ts.min() > 30 else np.nan)
    else:
        r["atm_iv_30"] = np.nan
    r["term_ratio"] = r["atm_iv_front"] / r["atm_iv_30"] if r["atm_iv_30"] and np.isfinite(r["atm_iv_30"]) else np.nan
    r["skew25_30"] = np.nan
    if exps:
        t30 = min(exps, key=lambda t: abs(t - 30)); e = d[(d.dte == t30) & (d.implied_volatility > 0) & np.isfinite(d.delta)]
        pc, cc = e[~e.is_call], e[e.is_call]
        if len(pc) and len(cc):
            r["skew25_30"] = float(_nearest(pc, "delta", -0.25).implied_volatility.iloc[0] - _nearest(cc, "delta", 0.25).implied_volatility.iloc[0])
    return r


def prepare(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]); df["expiration"] = pd.to_datetime(df["expiration"])
    df["dte"] = (df["expiration"] - df["date"]).dt.days
    df["is_call"] = df["type"].astype(str).str.lower().str.startswith("c")
    for c in ("strike", "volume", "open_interest", "implied_volatility", "delta", "gamma"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[["volume", "open_interest"]] = df[["volume", "open_interest"]].fillna(0)
    return df


def build(options, underlying):
    """options: raw chain rows (COLS); underlying: date + close. -> one row per day, oldest first."""
    o = prepare(options)
    u = underlying.assign(date=pd.to_datetime(underlying["date"])).set_index("date")["close"].astype(float)
    rows = []
    for day, d in o.groupby("date", sort=True):
        spot = float(u.get(day, np.nan))
        if not np.isfinite(spot): continue
        rows.append({"date": day.strftime("%Y-%m-%d"), **day_row(d, spot)})
    t = pd.DataFrame(rows)
    if t.empty: return t
    g = t["gex_norm"]
    t["gex_rank_252"] = [np.nan if i < 252 or not np.isfinite(g.iloc[i]) else float((g.iloc[i - 252:i].dropna() < g.iloc[i]).mean())
                         for i in range(len(t))]
    order = ["date", "spot", "gex_norm", "gex_rank_252", "oi_calls", "oi_puts", "vol_calls", "vol_puts",
             "atm_iv_front", "atm_iv_30", "term_ratio", "skew25_30", "n_contracts"]
    return t[order].round(6)


def main(sym="QQQ"):
    import pyarrow.parquet as pq
    tmp = os.environ.get("RUNNER_TEMP", "/tmp"); s = sym.lower()
    paths = {}
    for kind in ("options", "underlying"):
        p = os.path.join(tmp, f"{s}_{kind}.parquet")
        if not os.path.exists(p):
            print(f"downloading {kind} for {sym}...", flush=True)
            urllib.request.urlretrieve(BASE.format(s, kind), p)
        paths[kind] = p; print(f"  {kind}: {os.path.getsize(p) / 1e6:.0f} MB", flush=True)
    have = pq.ParquetFile(paths["options"]).schema_arrow.names
    missing = [c for c in COLS if c not in have]
    if missing: raise SystemExit(f"unexpected file layout, missing columns {missing}; columns are {have}")
    opts = pq.read_table(paths["options"], columns=COLS).to_pandas()
    und = pq.read_table(paths["underlying"]).to_pandas()
    print(f"  {len(opts):,} option rows, {opts['date'].nunique():,} days", flush=True)
    t = build(opts, und)
    os.makedirs(OUT, exist_ok=True); out = os.path.join(OUT, f"{sym.upper()}_daily.csv")
    t.to_csv(out, index=False)
    ok = t.notna().mean().round(3).to_dict()
    print(f"wrote {out}: {len(t)} days {t.date.iloc[0]} .. {t.date.iloc[-1]}; share filled per column: {ok}", flush=True)


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["QQQ"]): main(a)
