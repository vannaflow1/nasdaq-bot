"""
options_nerd.py - the deep options read on QQQ from today's chain: dealer greek exposures
(gamma, vanna, charm), the volatility surface (term structure, skew, butterfly), implied
moves per expiry, IV percentile, variance risk premium, max pain and big OI strikes.

Every number comes with a plain-English line. Black-Scholes (r = q = 0) is used for the
greeks the chain doesn't provide. Dealer positioning assumes the usual convention
(dealers long calls, short puts) - nobody can see the real book; treat as an estimate.

Validation status: gamma regime -> next-day volatility is VALIDATED (2011-2025).
Vanna, charm, skew, VRP, put/call were tested as extra inputs to the brain's range
forecast and did NOT add accuracy. They are context, not signals.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
IVH = os.path.join(HERE, "iv30_history.csv")


def _bs(S, K, T, iv):
    T = np.maximum(T, 0.25 / 365)
    iv = np.clip(iv, 0.03, 3)
    d1 = (np.log(S / K) + 0.5 * iv * iv * T) / (iv * np.sqrt(T))
    d2 = d1 - iv * np.sqrt(T)
    pdf = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi)
    return d1, d2, pdf, T


def _money(x):
    a = abs(x)
    s = f"${a/1e9:.1f}B" if a >= 1e9 else f"${a/1e6:.0f}M" if a >= 1e6 else f"${a/1e3:.0f}K"
    return s


def exposures(d, S):
    """Dealer hedge flows in $ of QQQ."""
    g = d[(d.open_interest > 0) & (d.dte >= 0) & (d.dte <= 60) & (d.iv > 0.03)].copy()
    d1, d2, pdf, T = _bs(S, g.strike.values, g.dte.values / 365, g.iv.values)
    sg = np.where(g.is_call, 1.0, -1.0)                 # dealer: long calls, short puts
    oi = g.open_interest.values * 100
    gamma = pdf / (S * g.iv.values * np.sqrt(T))
    vanna = -pdf * d2 / g.iv.values                     # d(delta)/d(vol)
    charm = pdf * d2 / (2 * T) / 365                    # d(delta)/d(day passing)
    gex1 = float((sg * gamma * oi * S * S * 0.01).sum())     # $ delta change per +1% move
    # dealer delta change -> they trade the opposite to stay hedged
    van_flow = float(-(sg * vanna * (-0.01) * oi).sum() * S)  # hedge $ if IV drops 1 vol pt
    chm_flow = float(-(sg * charm * oi).sum() * S)            # hedge $ per day from time decay
    near = g.dte <= 7
    chm_week = float(-(sg[near.values] * charm[near.values] * oi[near.values]).sum() * S)
    return {"gex1": gex1, "vanna_flow": van_flow, "charm_flow": chm_flow, "charm_week": chm_week}


def surface(d, S, ts):
    rows = []
    x = d[(d.bid > 0) & (d.ask > d.bid) & (d.dte >= 1) & (d.dte <= 70)]
    for e, g in x.groupby("expiration"):
        c = g[g.is_call].set_index("strike"); p = g[~g.is_call].set_index("strike")
        ks = c.index.intersection(p.index)
        if len(ks) < 5:
            continue
        k = ks[np.abs(ks - S).argmin()]
        strad = float(c.mid[k] + p.mid[k])
        atm = float((c.iv[k] + p.iv[k]) / 2)
        put25 = g[~g.is_call & g.delta.between(-.3, -.2)].iv.median()
        call25 = g[g.is_call & g.delta.between(.2, .3)].iv.median()
        rows.append({"exp": e, "dte": int(g.dte.iloc[0]), "atm": atm, "move": strad / S,
                     "rr": put25 - call25, "fly": (put25 + call25) / 2 - atm})
    return pd.DataFrame(rows).sort_values("exp")


def max_pain(d):
    fri = d[(d.expiration.dt.dayofweek == 4) & d.expiration.dt.day.between(15, 21) & (d.dte >= 0)]
    if fri.empty:
        return None, None
    e = fri.expiration.min(); g = fri[fri.expiration == e]
    ks = np.sort(g.strike.unique())
    c = g[g.is_call].groupby("strike").open_interest.sum(); p = g[~g.is_call].groupby("strike").open_interest.sum()
    pay = [float((c * np.maximum(K - c.index, 0)).sum() + (p * np.maximum(p.index - K, 0)).sum()) for K in ks]
    return e, float(ks[int(np.argmin(pay))])


def iv_pct(iv30, ts, write=True):
    h = pd.read_csv(IVH, parse_dates=["date"]) if os.path.exists(IVH) else pd.DataFrame(columns=["date", "iv30"])
    if write and np.isfinite(iv30):
        h = pd.concat([h[h.date != pd.Timestamp(ts)], pd.DataFrame([{"date": pd.Timestamp(ts), "iv30": round(iv30, 5)}])])
        h.sort_values("date").to_csv(IVH, index=False, date_format="%Y-%m-%d")
    return float((h.iv30 < iv30).mean())


def read(d, S, ts, rv20=None, nq_ratio=None, write=True):
    """Returns the 'options nerd' lines (plain English)."""
    L = []
    sf = surface(d, S, ts)
    ex = exposures(d, S)
    iv30 = sf[(sf.dte >= 20) & (sf.dte <= 45)].atm.mean() if len(sf) else np.nan
    pct = iv_pct(iv30, ts, write)
    L.append(f"VOLATILITY: 30-day IV {iv30*100:.1f}% -> higher than {pct:.0%} of days since 2011")
    L.append("  " + ("options are CHEAP vs history" if pct < .3 else "options are EXPENSIVE vs history" if pct > .7
                     else "options are about average-priced vs history"))
    if rv20 and np.isfinite(rv20):
        vrp = iv30 - rv20
        L.append(f"  realized vol (20d) {rv20*100:.1f}% -> premium {vrp*100:+.1f} pts: " +
                 ("options price MORE movement than the market is delivering (sellers' edge, usual state)" if vrp > 0.01 else
                  "options price LESS movement than the market is delivering (buyers favored)" if vrp < -0.01 else
                  "options priced about in line with recent movement"))
    if len(sf):
        L.append("")
        L.append("TERM STRUCTURE - what each expiry prices (QQQ move to expiry):")
        for r in sf.head(6).itertuples():
            pts = f" (~{r.move * S * nq_ratio:,.0f} NQ pts)" if nq_ratio else ""
            L.append(f"  {r.exp:%a %d %b} ({r.dte}d): ±{r.move*100:.2f}%{pts}, ATM IV {r.atm*100:.1f}%")
        fr = sf[sf.dte >= 5]                            # skip 1-4 day expiries (overnight noise)
        front = fr.atm.iloc[0] if len(fr) else np.nan
        back = sf[sf.dte >= 20].atm.iloc[0] if (sf.dte >= 20).any() else np.nan
        if np.isfinite(back) and np.isfinite(front):
            L.append("  " + (f"INVERTED (front {front*100:.1f}% > month {back*100:.1f}%): market expects trouble NOW - event or stress"
                             if front > back * 1.03 else
                             f"normal upward slope (front {front*100:.1f}% < month {back*100:.1f}%): calm near term"
                             if front < back * 0.97 else "flat: no special near-term fear"))
        m = sf[(sf.dte >= 20) & (sf.dte <= 45)]
        if len(m) and np.isfinite(m.rr.iloc[0]):
            rr, fly = m.rr.iloc[0], m.fly.iloc[0]
            L.append("")
            L.append(f"SKEW (~30d): 25-delta puts {rr*100:+.1f} vol pts vs calls; wings {fly*100:+.1f} pts vs ATM")
            ratio = rr / m.atm.iloc[0]                     # history 2011-25: 10%=0.20, median 0.32, 90%=0.41
            L.append("  " + ("STEEP put skew (top 10% since 2011) - crash protection in heavy demand, fear elevated"
                             if ratio > 0.41 else
                             "FLAT skew (bottom 10% since 2011) - calls bid, upside chase / complacency"
                             if ratio < 0.20 else
                             "normal put skew - people always pay a bit extra for crash protection"))
    L.append("")
    L.append("DEALER GREEKS (estimate - assumes dealers long calls / short puts):")
    L.append(f"  GAMMA: per 1% QQQ move dealers trade {_money(ex['gex1'])} " +
             ("AGAINST the move (they dampen it)" if ex["gex1"] > 0 else "WITH the move (they amplify it)"))
    v = ex["vanna_flow"]
    L.append(f"  VANNA: if IV drops 1 pt, dealers {'BUY' if v > 0 else 'SELL'} ~{_money(v)} of QQQ" +
             (" -> falling vol supports the market (classic 'vanna rally')" if v > 0 else " -> falling vol adds selling"))
    c = ex["charm_flow"]
    cw = ex["charm_week"]
    L.append(f"  CHARM: time decay alone makes dealers {'BUY' if c > 0 else 'SELL'} ~{_money(c)} per day overall;"
             f" this week's expiries alone: {'BUY' if cw > 0 else 'SELL'} {_money(cw)}/day (biggest into expiry)")
    e, mp = max_pain(d)
    if mp:
        L.append("")
        L.append(f"MAX PAIN {e:%d %b} monthly: {mp:.0f} (QQQ now {S:.2f}) - where option buyers lose most."
                 " Weak magnet at best, mostly in expiry week.")
    big = d[(d.dte >= 0) & (d.dte <= 35)].groupby(["strike", "is_call"]).open_interest.sum()
    if len(big):
        cs = big.xs(True, level=1).nlargest(3); ps = big.xs(False, level=1).nlargest(3)
        L.append(f"BIGGEST OI (next 5 weeks): calls {', '.join(f'{k:.0f}' for k in cs.index)} | "
                 f"puts {', '.join(f'{k:.0f}' for k in ps.index)}")
    if "volume" in d:
        vol = pd.to_numeric(d.volume, errors="coerce").fillna(0)
        pcv = vol[~d.is_call].sum() / max(vol[d.is_call].sum(), 1)
        L.append(f"PUT/CALL volume today {pcv:.2f} " + ("(heavy hedging)" if pcv > 1.8 else "(call-heavy, risk-on)" if pcv < 1.0 else "(normal)"))
    L.append("")
    L.append("Status: gamma regime = validated. Everything else = context; tested, did NOT improve forecasts.")
    return L
