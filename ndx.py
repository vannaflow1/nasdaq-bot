"""
NDX index options (roots NDX and NDXP) from the free CBOE delayed feed.

QQQ options are only part of Nasdaq dealer gamma; NDX options carry a large share
of it. We have NO historical NDX chain, so the combined QQQ+NDX reading is NOT
validated: it is logged daily into ndx_history.csv and only gets a rank once
~126 trading days exist. Until then the validated QQQ rank stays the headline.
"""
import gzip, json, urllib.request
import numpy as np
import pandas as pd

URL = "https://cdn-api.cboe.com/api/global/delayed_quotes/options/_NDX.json"
UA = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}


def fetch(url=URL, path=None, timeout=180):
    if path:
        return json.load(open(path))
    resp = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
    body = resp.read()
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    return json.loads(body)


def parse(raw, roots=("NDX", "NDXP")):
    d = pd.DataFrame(raw["data"]["options"])
    sym = d["option"].str.extract(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")
    d = d[sym[0].isin(roots)].copy()
    sym = sym.loc[d.index]
    d["expiration"] = pd.to_datetime(sym[1], format="%y%m%d")
    d["is_call"] = sym[2] == "C"
    d["strike"] = sym[3].astype(float) / 1000.0
    for c in ["bid", "ask", "open_interest", "gamma", "iv", "delta"]:
        d[c] = pd.to_numeric(d.get(c, 0), errors="coerce").fillna(0.0)
    if "last_trade_time" in d:
        ltt = pd.to_datetime(d["last_trade_time"], errors="coerce").dropna()
        ts = ltt.max().normalize() if len(ltt) else pd.Timestamp(raw["timestamp"][:10])
    else:
        ts = pd.Timestamp(raw["timestamp"][:10])
    d["dte"] = (d.expiration - ts).dt.days
    d["mid"] = (d.bid + d.ask) / 2
    return ts, d


def spot_by_parity(d):
    x = d[(d.dte >= 1) & (d.dte <= 45) & (d.bid > 0) & (d.ask > 0)]
    if x.empty:
        return float("nan")
    x = x[x.dte == x.dte.min()]
    c = x[x.is_call].groupby("strike").mid.mean()
    p = x[~x.is_call].groupby("strike").mid.mean()
    cp = pd.concat([c.rename("c"), p.rename("p")], axis=1).dropna()
    if cp.empty:
        return float("nan")
    k = (cp.c - cp.p).abs().idxmin()
    return float(k + cp.at[k, "c"] - cp.at[k, "p"])


def dollar_gex(d, S, mult=100):
    """Net dealer gamma in $ per 1% move (calls +, puts -), same convention as QQQ."""
    x = d[(d.open_interest > 0) & (d.dte >= 0)]
    sign = np.where(x.is_call, 1.0, -1.0)
    return float((sign * x.gamma * x.open_interest * mult * S * S * 0.01).sum())


def gamma_ratio(d, S):
    """CBOE gamma vs Black-Scholes, to catch convention changes (should be ~1)."""
    try:
        import greeks
    except ImportError:
        return None
    x = d[(d.dte >= 5) & (d.dte <= 60) & (d.iv > 0.05) & (d.gamma > 0) & (d.delta.abs().between(.3, .7))]
    if len(x) < 10:
        return None
    g = greeks.gamma(S, x.strike.values, x.dte.values / 365.0, 0.04, x.iv.values)
    return float(np.median(x.gamma.values / g))
