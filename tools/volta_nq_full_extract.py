"""Volta - pack the FULL-session NQ 1-minute file (incl. London / Asia) for the owner-model test. Runs on your PC.

Put this file in your NQ_backtest folder (the folder with the NQ 1-minute CSV Volta's data originally came from) and run:
    python volta_nq_full_extract.py
It finds the 1-minute NQ CSV (';' separated, European decimals, newest-first, Chicago/CME time), reads it, sorts it
oldest-first, keeps date-time, open, high, low, close, volume, and writes small files:
    volta_out/nq_full/NQ_1m_<year>.parquet   (about 3-6 MB each)
    volta_out/nq_full.zip                    (all years in one zip - attach this to the chat)
Nothing is changed in your folder. If it cannot find the file, run it with the path:  python volta_nq_full_extract.py "C:\\path\\to\\file.csv"
"""
import glob, os, sys, zipfile
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "volta_out", "nq_full")


def find_csv():
    if len(sys.argv) > 1: return sys.argv[1]
    cands = [f for f in glob.glob(os.path.join(ROOT, "**", "*.*"), recursive=True)
             if f.lower().endswith((".csv", ".txt")) and "nq" in os.path.basename(f).lower()]
    one = [f for f in cands if any(k in os.path.basename(f).lower() for k in ("1m", "1 m", "1min", "1 min", "1-min", "minute", "_1_", " 1."))]
    pick = sorted(one or cands, key=os.path.getsize, reverse=True)
    print("candidates:", *[f"{os.path.basename(f)} ({os.path.getsize(f) / 1e6:.0f} MB)" for f in pick[:6]], sep="\n  ")
    if not pick: sys.exit("No NQ csv/txt found - run again with the file path as argument.")
    return pick[0]


def read(fn):
    head = open(fn, "r", errors="replace").read(4000).splitlines()
    sep = ";" if head[0].count(";") >= head[0].count(",") else ","
    dec = "," if sep == ";" else "."
    df = pd.read_csv(fn, sep=sep, decimal=dec, thousands="." if dec == "," else None, low_memory=False, dtype=str)
    for col in df.columns:                                     # numbers like 3.575,75 (thousands '.', decimal ',')
        if col.strip().lower() not in ("date", "time", "datetime", "timestamp", "symbol", "contract", "ticker"):
            x = df[col].astype(str).str.strip()
            if dec == ",": x = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(x, errors="coerce")
    cols = {c: c.strip().lower() for c in df.columns}; df = df.rename(columns=cols)
    pick = lambda *ks: next((c for c in df.columns if any(k == c or c.startswith(k) for k in ks)), None)
    o, h, l, c = pick("open", "o"), pick("high", "h"), pick("low", "l"), pick("close", "last", "c")
    v = pick("volume", "vol", "v")
    d, t = pick("date"), pick("time")
    dt = pick("datetime", "timestamp", "date time", "date_time")
    raw = (df[dt] if dt else (df[d].astype(str) + " " + df[t].astype(str)) if (d and t) else df[d or df.columns[0]]).astype(str).str.strip()
    ts = None
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M:%S %p", "%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        t_ = pd.to_datetime(raw, format=fmt, errors="coerce")
        if t_.notna().mean() > 0.95: ts = t_; print("date format:", fmt); break
    if ts is None: ts = pd.to_datetime(raw, errors="coerce")
    out = pd.DataFrame({"ts": ts, "open": pd.to_numeric(df[o], errors="coerce"), "high": pd.to_numeric(df[h], errors="coerce"),
                        "low": pd.to_numeric(df[l], errors="coerce"), "close": pd.to_numeric(df[c], errors="coerce"),
                        "volume": pd.to_numeric(df[v], errors="coerce") if v else 0})
    sym = pick("symbol", "contract", "ticker")
    if sym: out["sym"] = df[sym].astype(str)
    return out.dropna(subset=["ts", "close"]).sort_values("ts").drop_duplicates("ts", keep="last").reset_index(drop=True)


def main():
    fn = find_csv(); print("reading", fn)
    df = read(fn)
    print(f"{len(df):,} bars  {df.ts.min()}  ->  {df.ts.max()}   columns: {list(df.columns)}")
    hrs = df.ts.dt.hour.value_counts().sort_index(); print("bars per hour (should cover the night too):", dict(hrs))
    os.makedirs(OUT, exist_ok=True)
    for y, g in df.groupby(df.ts.dt.year):
        p = os.path.join(OUT, f"NQ_1m_{y}.parquet")
        try: g.to_parquet(p, index=False)
        except ImportError: p = p.replace(".parquet", ".csv.gz"); g.to_csv(p, index=False)      # no pyarrow: compressed csv
        print(" ", os.path.basename(p), f"{os.path.getsize(p) / 1e6:.1f} MB")
    z = os.path.join(ROOT, "volta_out", "nq_full.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for p in sorted(glob.glob(os.path.join(OUT, "NQ_1m_*"))): zf.write(p, os.path.basename(p))
    print(f"\nDONE -> {z} ({os.path.getsize(z) / 1e6:.0f} MB). Attach it to the chat (or the yearly files if it is too big).")


if __name__ == "__main__":
    main()
