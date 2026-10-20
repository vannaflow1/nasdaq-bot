"""fetch_macro.py - free daily market-wide context for the research engine (Yahoo daily closes, full history):
VIX family (fear + term structure), ES / S&P 500 (is tech leading?), 10-year yield and the dollar.
Writes knowledge/macro_daily.csv, one row per US trading day; every value is known at that day's close."""
import os, sys, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import json, urllib.request
from datetime import datetime, timezone
UA = {"User-Agent": "Mozilla/5.0"}


def daily(sym):
    """Full daily history (Yahoo silently returns MONTHLY bars for range=max, so ask by explicit dates)."""
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?interval=1d"
         f"&period1=1262304000&period2={int(datetime.now(timezone.utc).timestamp())}")
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["chart"]["result"][0]
    idx = [pd.Timestamp(datetime.fromtimestamp(t, timezone.utc).date()) for t in r["timestamp"]]
    c = pd.Series(r["indicators"]["quote"][0]["close"], index=idx, dtype=float)
    return c[~c.index.duplicated(keep="last")].dropna()


SYMS = {"vix": "^VIX", "vix9d": "^VIX9D", "vix3m": "^VIX3M", "vvix": "^VVIX", "vix1d": "^VIX1D", "es": "ES=F", "nq": "NQ=F",
        "spx": "^GSPC", "tnx": "^TNX", "dxy": "DX-Y.NYB"}


def main():
    raw = {}
    for k, s in SYMS.items():
        for a in range(3):
            try:
                raw[k] = daily(s); print(f"{k:6s} {s:9s} {len(raw[k])} days from {raw[k].index.min().date()}"); break
            except Exception as e:
                print(k, "retry", e); time.sleep(3)
    D = pd.DataFrame(raw).sort_index()
    D = D[D.index >= "2010-01-01"]
    D = D[D.spx.notna()] if "spx" in D else D
    D = D.ffill(limit=1)                                # futures/FX holidays: carry one day so returns stay daily
    O = pd.DataFrame(index=D.index)
    for k in ("vix", "vix9d", "vix3m", "vvix", "vix1d"):
        if k in D: O[k] = D[k]
    if {"vix9d", "vix"} <= set(D): O["vix_term"] = D.vix9d / D.vix                  # > 1 = near-term fear above 30-day
    if {"vix", "vix3m"} <= set(D): O["vix_curve"] = D.vix / D.vix3m                 # > 1 = inverted curve (stress)
    if "vix" in D: O["vix_chg"] = D.vix.pct_change() * 100
    if {"vvix", "vix"} <= set(D): O["vvix_vix"] = D.vvix / D.vix
    if "es" in D: O["es_ret"] = D.es.pct_change() * 100; O["es_ret5"] = D.es.pct_change(5) * 100
    if {"es", "nq"} <= set(D): O["nq_vs_es"] = (D.nq.pct_change() - D.es.pct_change()) * 100; O["nq_vs_es5"] = (D.nq.pct_change(5) - D.es.pct_change(5)) * 100
    if "spx" in D: O["spx_ret"] = D.spx.pct_change() * 100
    if "tnx" in D: O["us10y"] = D.tnx; O["us10y_chg_bp"] = D.tnx.diff() * 100 / (10 if D.tnx.median() > 20 else 1)
    if "dxy" in D: O["dxy_ret"] = D.dxy.pct_change() * 100
    O.index.name = "date"
    O.round(5).to_csv(os.path.join(HERE, "knowledge", "macro_daily.csv"))
    print(O.shape, O.index.min().date(), "->", O.index.max().date()); print(O.tail(2).T.round(3).to_string())


if __name__ == "__main__":
    main()
