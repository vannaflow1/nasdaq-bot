"""tools/bar_archive.py - nightly archive of 1-minute futures bars (expert review, 21 Oct 2026: the most recent months are the
most valuable test data and were missing). Yahoo's free chart API returns the last ~5 days of 1-minute bars, so running
this every weekday keeps an unbroken record from now on. Bars are appended to knowledge/data/archive/<MKT>_<YYYY-MM>.csv.gz
(Chicago time, continuous front contract as Yahoo serves it), de-duplicated by timestamp. A gap report is written to
knowledge/data/archive/gaps.txt (weekdays with fewer than 1,000 bars = a missing or partial day).
Older history (Feb-Oct 2026) still needs a one-off backfill from a data vendor or the owner's platform."""
import os, sys, json, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "knowledge", "data", "archive")
SYMS = {"NQ": "NQ%3DF", "ES": "ES%3DF", "RTY": "RTY%3DF", "YM": "YM%3DF", "GC": "GC%3DF", "CL": "CL%3DF"}
CT = ZoneInfo("America/Chicago")


def fetch(sym):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=5d&includePrePost=true"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"ts": [datetime.fromtimestamp(t, timezone.utc).astimezone(CT).replace(tzinfo=None) for t in r["timestamp"]],
                       "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q.get("volume")})
    return df.dropna(subset=["close"])


def main():
    os.makedirs(OUT, exist_ok=True); report = []
    for mk, sym in SYMS.items():
        try:
            df = fetch(sym)
        except Exception as e:
            report.append(f"{mk}: fetch failed {type(e).__name__}"); continue
        for ym, g in df.groupby(df.ts.dt.strftime("%Y-%m")):
            f = os.path.join(OUT, f"{mk}_{ym}.csv.gz")
            old = pd.read_csv(f, parse_dates=["ts"]) if os.path.exists(f) else pd.DataFrame(columns=g.columns)
            new = pd.concat([old, g]).drop_duplicates("ts", keep="last").sort_values("ts")
            new.to_csv(f, index=False, compression="gzip")
        report.append(f"{mk}: {len(df)} bars {df.ts.min()} .. {df.ts.max()}")
    gaps = []                                                   # weekdays with too few bars across the archive
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".csv.gz"): continue
        d = pd.read_csv(os.path.join(OUT, f), parse_dates=["ts"]); c = d.groupby(d.ts.dt.date).size()
        for day, n in c.items():
            if pd.Timestamp(day).weekday() < 5 and n < 1000: gaps.append(f"{f.split('_')[0]} {day}: {n} bars")
    open(os.path.join(OUT, "gaps.txt"), "w").write("\n".join(gaps[-200:]) + "\n")
    print("\n".join(report)); print(f"{len(gaps)} partial days in the archive")


if __name__ == "__main__":
    main()
