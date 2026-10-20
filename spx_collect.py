"""spx_collect.py - SPX options (CBOE delayed chain) summarised once per evening into knowledge/spx_daily.csv:
dealer gamma (same convention as QQQ), 0DTE share, ATM IV, skew. No free SPX history exists, so Volta builds its own;
after ~6-12 months the research engine can test whether SPX positioning beats QQQ's."""
import gzip, json, os, sys, urllib.request
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import qqq_gex_daily as q, brain
URL = "https://cdn-api.cboe.com/api/global/delayed_quotes/options/_SPX.json"
OUT = os.path.join(HERE, "knowledge", "spx_daily.csv")


def load():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    body = urllib.request.urlopen(req, timeout=240).read()
    if body[:2] == b"\x1f\x8b": body = gzip.decompress(body)
    print(f"got {len(body) / 1e6:.1f} MB")
    raw = json.loads(body); d = pd.DataFrame(raw["data"]["options"])
    ltt = pd.to_datetime(d.get("last_trade_time"), errors="coerce").dropna() if "last_trade_time" in d else pd.Series(dtype="datetime64[ns]")
    ts = ltt.max().normalize() if len(ltt) else pd.Timestamp(raw.get("timestamp", "")[:10])
    sym = d["option"].str.extract(r"^([A-Z]+?)W?(\d{6})([CP])(\d{8})$")
    d["expiration"] = pd.to_datetime(sym[1], format="%y%m%d", errors="coerce"); d["is_call"] = sym[2] == "C"
    d["strike"] = sym[3].astype(float) / 1000.0
    d = d[sym[0].isin(["SPX"]) & d.expiration.notna()].copy()
    for c in ["bid", "ask", "open_interest", "gamma", "iv", "delta"]:
        d[c] = pd.to_numeric(d.get(c), errors="coerce").fillna(0.0)
    d["date"] = ts; d["dte"] = (d.expiration - ts).dt.days; d["mid"] = (d.bid + d.ask) / 2
    return ts, d, raw


def main():
    ts, d, raw = load()
    try:
        S = q.spot_by_parity(d)
    except Exception:
        S = float(raw.get("data", {}).get("current_price") or brain.yahoo("^GSPC", "5d").close.iloc[-1])
    oi = d[(d.open_interest > 0) & (d.dte >= 0)]
    near = d[(d.dte >= 1) & (d.dte <= 7) & (d.iv > 0.03)]
    e = near.expiration.min() if len(near) else None
    atm = d[(d.expiration == e) & d.delta.abs().between(.4, .6) & (d.iv > 0.03)].iv.mean() if e is not None else np.nan
    m30 = d[(d.dte >= 20) & (d.dte <= 45) & (d.iv > 0.03)]
    put25 = m30[~m30.is_call & m30.delta.between(-.3, -.2)].iv.mean(); call25 = m30[m30.is_call & m30.delta.between(.2, .3)].iv.mean()
    atm30 = m30[m30.delta.abs().between(.4, .6)].iv.mean()
    row = {"date": ts.date().isoformat(), "spx_spot": round(float(S), 2), "spx_gexn": round(float(q.gexn(d, S)), 4),
           "spx_0dte_share": round(float(oi[oi.dte <= 1].open_interest.sum() / max(oi.open_interest.sum(), 1)), 4),
           "spx_atm_iv": round(float(atm), 4) if np.isfinite(atm) else None,
           "spx_skew": round(float((put25 - call25) / atm30), 4) if np.isfinite(put25) and np.isfinite(call25) and atm30 else None,
           "spx_oi_total": int(oi.open_interest.sum()), "spx_contracts": int(len(d))}
    H = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame()
    H = pd.concat([H[H.get("date", pd.Series(dtype=str)) != row["date"]] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values("date")
    H.to_csv(OUT, index=False); print(row); print(len(H), "days collected")


if __name__ == "__main__":
    main()
