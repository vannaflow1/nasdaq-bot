"""spx_morning.py - before the NY open: reads the SPX weekly option chain (CBOE, yesterday's close quotes + this
morning's open interest) and adjusts the brain's full-day range by where the dealer gamma and the call/put walls sit.

Tested on 7 years of SPX weekly options tick data (2019-2025, 1,711 sessions): adding dealer gamma + the distance
between the walls (vs their own 60-day normal) to the brain's features cut the out-of-sample range error by 1.9%,
better in 5/5 years, placebo p<0.005. More dealer gamma -> slightly smaller day; walls unusually far apart -> bigger
day. Typical change: -9% .. +8%. knowledge/spx_morning.csv keeps the daily readings (first 60 rows = 2025-26 history).
Coefficients: models/spx_adj.json. Same definitions as the history (tools/spx_features.py). Any failure = no change."""
import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CT = ZoneInfo("America/Chicago")
STATUS, MODEL = os.path.join(HERE, "status.json"), os.path.join(HERE, "models", "spx_adj.json")
LOG = os.path.join(HERE, "knowledge", "spx_morning.csv")


def bs_price(S, K, T, v, call):
    d1 = (np.log(S / K) + 0.5 * v * v * T) / (v * np.sqrt(T)); d2 = d1 - v * np.sqrt(T)
    return np.where(call, S * norm.cdf(d1) - K * norm.cdf(d2), K * norm.cdf(-d2) - S * norm.cdf(-d1))


def implied_vol(P, S, K, T, call):
    lo, hi = np.full(P.shape, 0.01), np.full(P.shape, 4.0)
    intrinsic = np.where(call, np.maximum(S - K, 0), np.maximum(K - S, 0))
    ok = (P > intrinsic + 0.01) & (T > 0)
    with np.errstate(all="ignore"):
        for _ in range(45):
            mid = (lo + hi) / 2; pm = bs_price(S, K, T, mid, call)
            hi = np.where(pm > P, mid, hi); lo = np.where(pm > P, lo, mid)
    return np.where(ok, (lo + hi) / 2, np.nan)


def gamma(S, K, T, v):
    with np.errstate(all="ignore"):
        d1 = (np.log(S / K) + 0.5 * v * v * T) / (v * np.sqrt(T)); return norm.pdf(d1) / (S * v * np.sqrt(T))


def features(today):
    import spx_collect as C
    ts, d, raw = C.load()                                         # ts = last trading day of the quotes (yesterday)
    d = d[d["option"].str.startswith("SPXW")].copy()             # weeklies, like the history
    S = float(raw.get("data", {}).get("current_price") or 0) or float(C.q.spot_by_parity(d))
    today = pd.Timestamp(today)
    d["dte"] = (d.expiration - today).dt.days
    d = d[(d.dte >= 0) & (d.dte <= 7) & (d.ask > 0) & ((d.strike / S - 1).abs() <= 0.10)].copy()
    if len(d) < 50: raise RuntimeError(f"only {len(d)} contracts")
    call = d.is_call.values; K = d.strike.values
    T_iv = ((d.expiration - pd.Timestamp(ts).normalize()).dt.days * 1440 + 10).values / (365 * 1440)
    d["iv"] = implied_vol(d.mid.values, S, K, T_iv, call)
    d["iv"] = d.groupby("expiration").iv.transform(lambda s: s.fillna(s.median()))
    d = d[d.iv.notna()]
    call = d.is_call.values; K = d.strike.values; oi = d.open_interest.values
    T0 = (d.dte.values * 1440 + 390) / (365 * 1440)
    g1 = gamma(S, K, T0, d.iv.values)
    gex = np.nansum(np.where(call, 1.0, -1.0) * oi * g1 * S * S * 0.01 * 100) / 1e9 / (S / 4000) ** 2
    near = np.abs(K / S - 1) <= 0.03; gm = g1 * oi
    up = call & (K > S) & near; dn = (~call) & (K < S) & near
    cw = K[up][np.nanargmax(gm[up])] if up.any() else np.nan
    pw = K[dn][np.nanargmax(gm[dn])] if dn.any() else np.nan
    return {"spot": round(S, 2), "gex": round(float(gex), 3), "call_wall": float(cw), "put_wall": float(pw),
            "span": round(float((cw / S - 1) * 100 - (pw / S - 1) * 100), 3), "quotes_from": str(pd.Timestamp(ts).date()), "contracts": int(len(d))}


def adjust(force=False):
    now = datetime.now(CT); today = str(now.date())
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    bp = st.get("brain_pred") or {}
    if bp.get("date") != today or (bp.get("spx_factor") and not force): return None
    m = json.load(open(MODEL))
    f = features(now.date())
    if not np.isfinite(f["span"]): raise RuntimeError("no walls found")
    H = pd.read_csv(LOG) if os.path.exists(LOG) else pd.DataFrame(columns=["date", "span"])
    prev = H[H.date.astype(str) < today].dropna(subset=["span"]).tail(60)
    if len(prev) < 20: raise RuntimeError("not enough wall history yet")
    f["span_rel"] = round(f["span"] / max(float(prev.span.median()), 0.05), 3)      # walls vs their own last-60-day normal
    adj = m["c_gex"] * (f["gex"] - m["m_gex"]) + m["c_span_rel"] * (f["span_rel"] - m["m_span_rel"])
    fac = float(np.exp(np.clip(adj, -0.12, 0.12)))
    raw = {k: bp[k] for k in ("pred", "high_mid", "high_far", "low_mid", "low_far") if k in bp}
    nq = float(bp.get("nq") or 0)
    bp["raw"] = raw; bp["spx_factor"] = round(fac, 4)
    bp["pred"] = round(raw["pred"] * fac, 5)
    for k in ("high_mid", "high_far", "low_mid", "low_far"):
        if k in raw and nq: bp[k] = round(nq + (raw[k] - nq) * fac, 2)
    st["brain_pred"] = bp
    word = "bigger" if fac > 1.005 else "smaller" if fac < 0.995 else "unchanged"
    st["spx_morning"] = [f"SPX DEALER CHECK ({today}): dealer gamma {f['gex']:+.1f} (avg {m['m_gex']:+.1f}), SPX walls {f['put_wall']:.0f} / {f['call_wall']:.0f} "
                         f"({f['span_rel']:.1f}x their usual distance) -> today's range {word} ({fac - 1:+.1%})"]
    json.dump(st, open(STATUS, "w"), indent=1)
    row = {"date": today, **f, "factor": round(fac, 4), "pred_raw": raw["pred"], "pred": bp["pred"]}
    pd.concat([H[H.date.astype(str) != today], pd.DataFrame([row])], ignore_index=True).to_csv(LOG, index=False)
    print(st["spx_morning"][0])
    return fac


if __name__ == "__main__":
    if "--features" in sys.argv:
        print(features(datetime.now(CT).date()))
    else:
        print(adjust(force="--force" in sys.argv))
