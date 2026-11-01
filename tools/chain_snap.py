"""tools/chain_snap.py - intraday 0-DTE option chain snapshots (wish #23, 1 Nov 2026).
Ideas like short-vol straddles and gamma flips need intraday option prices, which no free history provides. From now on
this records them: during the US cash session (09:25-16:05 New York, weekdays) it saves the CBOE delayed chain for QQQ and
NDX - the nearest two expirations (0-DTE + next), strikes within +-STRIKE_BAND of spot - every ~5 minutes (GitHub cron;
runs can be delayed or dropped, so gaps are expected and logged).
Data is delayed ~15 min by CBOE; the snapshot keeps CBOE's own quote timestamp ('quote_ts') so research must align on that,
never on the fetch time. One small file per snapshot (append-only, never rewritten - keeps git history lean):
  knowledge/data/chains/<SYM>/<YYYY-MM-DD>/<HHMM>.csv.gz   (HHMM = New York fetch time)
Research side only: nothing reads these files for live decisions. Usage: python tools/chain_snap.py [--force]"""
import gzip, json, os, sys, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "knowledge", "data", "chains")
SYMS = {"QQQ": "QQQ", "NDX": "_NDX"}
ROOTS = {"QQQ": ("QQQ",), "NDX": ("NDX", "NDXP")}
STRIKE_BAND = 0.04
N_EXP = 2
NY = ZoneInfo("America/New_York")
COLS = ["expiration", "dte", "cp", "strike", "bid", "ask", "last", "iv", "delta", "gamma", "theta", "vega",
        "volume", "open_interest", "last_trade_time"]


def in_session(now):
    if now.weekday() >= 5: return False
    m = now.hour * 60 + now.minute
    return 9 * 60 + 25 <= m <= 16 * 60 + 5


def fetch(code):
    u = f"https://cdn-api.cboe.com/api/global/delayed_quotes/options/{code}.json"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    body = urllib.request.urlopen(req, timeout=120).read()
    if body[:2] == b"\x1f\x8b": body = gzip.decompress(body)
    return json.loads(body)


def parse(raw, sym, today):
    """CBOE JSON -> tidy snapshot frame (nearest N_EXP expirations >= today, strikes near spot) + meta dict."""
    data = raw.get("data", {}); d = pd.DataFrame(data.get("options", []))
    meta = {"quote_ts": raw.get("timestamp"), "spot": data.get("current_price"), "rows_raw": int(len(d))}
    if d.empty: return d, meta
    s = d["option"].str.extract(r"^([A-Z]+?)(\d{6})([CP])(\d{8})$")
    d = d[s[0].isin(ROOTS[sym])].copy(); s = s.loc[d.index]
    d["expiration"] = pd.to_datetime(s[1], format="%y%m%d", errors="coerce")
    d["cp"] = s[2]; d["strike"] = s[3].astype(float) / 1000.0
    d = d[d.expiration.notna() & (d.expiration >= pd.Timestamp(today))]
    for c in ["bid", "ask", "last_trade_price", "iv", "delta", "gamma", "theta", "vega", "volume", "open_interest"]:
        d[c] = pd.to_numeric(d.get(c), errors="coerce")
    d["last"] = d.pop("last_trade_price")
    if "last_trade_time" not in d: d["last_trade_time"] = None
    exps = sorted(d.expiration.unique())[:N_EXP]
    d = d[d.expiration.isin(exps)]
    spot = pd.to_numeric(meta["spot"], errors="coerce")
    if np.isfinite(spot) and spot > 0:
        d = d[(d.strike / spot - 1).abs() <= STRIKE_BAND]
    d["dte"] = (d.expiration - pd.Timestamp(today)).dt.days
    d["expiration"] = d.expiration.dt.strftime("%Y-%m-%d")
    d = d[COLS].sort_values(["expiration", "strike", "cp"]).reset_index(drop=True)
    for c in ["iv", "delta", "gamma", "theta", "vega"]: d[c] = d[c].round(6)
    return d, meta


def save(d, meta, sym, now):
    folder = os.path.join(OUT, sym, now.strftime("%Y-%m-%d")); os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, now.strftime("%H%M") + ".csv.gz")
    if os.path.exists(path): return None                    # never overwrite a snapshot
    d = d.copy(); d.insert(0, "spot", meta["spot"]); d.insert(0, "quote_ts", meta["quote_ts"])
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(d.to_csv(index=False).encode())
    return path


def main(force=False):
    now = datetime.now(timezone.utc).astimezone(NY)
    if not (force or in_session(now)):
        print(f"outside the US session ({now:%a %H:%M} NY) - nothing to do"); return 0
    log = []
    for sym, code in SYMS.items():
        try:
            d, meta = parse(fetch(code), sym, now.date())
            p = save(d, meta, sym, now) if len(d) else None
            log.append(f"{now:%Y-%m-%d %H:%M} {sym} rows={len(d)} raw={meta['rows_raw']} quote_ts={meta['quote_ts']} "
                       f"{'saved' if p else 'skipped'}")
        except Exception as e:                                # one symbol failing never stops the other
            log.append(f"{now:%Y-%m-%d %H:%M} {sym} ERROR {type(e).__name__}: {str(e)[:120]}")
    os.makedirs(os.path.join(OUT, "log"), exist_ok=True)                 # one small log per day (no ever-growing file)
    with open(os.path.join(OUT, "log", now.strftime("%Y-%m-%d") + ".txt"), "a") as f: f.write("\n".join(log) + "\n")
    print("\n".join(log)); return 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))
