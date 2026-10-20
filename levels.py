"""
levels.py - expected range, gamma walls and earnings implied moves.

Expected range (validated): the next-expiry ATM straddle is what options price for the
next move. Backtest 2011-2025 (1-DTE QQQ straddles): realized/implied by gamma quintile
q1 0.96, q2 1.06, q3 1.05, q4 0.92, q5 0.82 (pooled), i.e. options price the move about
right except on high-gamma days, when they overprice it. Share of days that stayed inside
the priced move: ~55% normally, ~66-72% on high-gamma days.

Gamma walls (TESTED 2014-2025, 2,984 days, vs random levels at the same volatility-scaled
distance): the call wall is NOT resistance and the put wall is NOT support beyond chance.
When the put wall breaks, the drop ran ~0.08% further than past a random level (both halves
of the sample). Gamma flip: days with NQ below the flip averaged ~25-35% bigger next-day
ranges within every gamma tercile - real, but already mostly in the options-priced range.
"""
import gzip, json, urllib.request
from datetime import timedelta
import numpy as np
import pandas as pd

REALIZED_RATIO = {1: 0.96, 2: 1.06, 3: 1.05, 4: 0.92, 5: 0.82}
INSIDE_SHARE = {1: 0.58, 2: 0.56, 3: 0.55, 4: 0.58, 5: 0.68}
UA = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}


def _tdays(d0, d1):
    """Trading days from close d0 to close d1 (weekdays only, >=1)."""
    n = int(np.busday_count(d0.date(), d1.date()))
    return max(n, 1)


def atm_straddle(d, S, min_dte=1, expiry_on_or_after=None):
    """(expiry, straddle mid, strike) for the first expiry >= min_dte (or >= a date)."""
    x = d[(d.bid > 0) & (d.ask > d.bid)]
    x = x[x.dte >= min_dte]
    if expiry_on_or_after is not None:
        x = x[x.expiration >= pd.Timestamp(expiry_on_or_after)]
    if x.empty:
        return None
    e = x.expiration.min()
    x = x[x.expiration == e]
    c = x[x.is_call].groupby("strike").mid.mean()
    p = x[~x.is_call].groupby("strike").mid.mean()
    ks = c.index.intersection(p.index)
    if len(ks) == 0:
        return None
    k = ks[np.abs(ks - S).argmin()]
    return e, float(c[k] + p[k]), float(k)


def expected_range(qqq_chain, S_qqq, ts, quintile, nq_level):
    """Dict with implied and gamma-adjusted 1-day move, in % and NQ points."""
    r = atm_straddle(qqq_chain, S_qqq)
    if r is None:
        return None
    e, strad, _ = r
    per_day = strad / S_qqq / np.sqrt(_tdays(ts, e))
    ratio = REALIZED_RATIO.get(quintile, 1.0)
    return {"implied_pct": per_day * 100, "implied_pts": per_day * nq_level,
            "typical_pct": per_day * ratio * 100, "typical_pts": per_day * ratio * nq_level,
            "ratio": ratio, "inside": INSIDE_SHARE.get(quintile, 0.56), "nq": nq_level}


def range_lines(r):
    if not r:
        return ["  expected range: n/a"]
    lo, hi = r["nq"] - r["typical_pts"], r["nq"] + r["typical_pts"]
    note = ("options usually OVERprice moves on days like this" if r["ratio"] < 0.9 else
            "options price moves about right on days like this")
    return [f"  Options price a ±{r['implied_pts']:.0f} pt CLOSE-TO-CLOSE move in NQ futures ({r['implied_pct']:.2f}%).",
            f"  Gamma-adjusted: ±{r['typical_pts']:.0f} pts -> close likely between {lo:,.0f} and {hi:,.0f} (NQ futures prices)",
            f"  ({note}; ~{r['inside']:.0%} of such days closed inside). This is where the day ENDS, not how far it",
            "  swings: the high-to-low range is usually ~1.5-2x wider - see /brain for the full-day range."]


# ------------------------------------------------------------------ gamma walls (tested, see top)
def _bs_gamma(S, K, T, iv):
    S, K, T, iv = (np.asarray(v, dtype=float) for v in (S, K, T, iv))
    T = np.maximum(T, 1 / 365 / 4)
    iv = np.clip(iv, 0.05, 3)
    d1 = (np.log(S / K) + 0.5 * iv * iv * T) / (iv * np.sqrt(T))
    return np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi) / (S * iv * np.sqrt(T))


def walls(chains, nq_level, max_dte=35, band=0.06, bucket=None):
    """chains: list of (chain_df, spot, to_nq_factor). Returns dict of NQ-point levels."""
    if bucket is None:                                  # ~0.1% of the index, rounded (25 pts at NQ 29k)
        bucket = max(round(nq_level * 0.001 / 5) * 5, 1)
    rows = []
    for d, S, f in chains:
        x = d[(d.open_interest > 0) & (d.dte >= 0) & (d.dte <= max_dte) & (d.iv > 0.03)]
        x = x[(x.strike > S * (1 - 2 * band)) & (x.strike < S * (1 + 2 * band))]
        if x.empty:
            continue
        rows.append(pd.DataFrame({"K_nq": x.strike.to_numpy(float) * f, "S": float(S), "f": float(f),
                                  "K": x.strike.to_numpy(float),
                                  "tt": np.maximum(x.dte.to_numpy(float), 0.25) / 365.0,
                                  "iv": x.iv.to_numpy(float), "oi": x.open_interest.to_numpy(float),
                                  "call": x.is_call.to_numpy(bool)}))
    if not rows:
        return None
    a = pd.concat(rows, ignore_index=True)
    sign = np.where(a.call, 1.0, -1.0)
    # dollar gamma per 1% move at the current spot, per contract row (same convention as GEX)
    g_now = _bs_gamma(a.S.values, a.K.values, a.tt.values, a.iv.values)
    dg = sign * g_now * a.oi.values * 100 * a.S.values ** 2 * 0.01
    a["dg"] = dg
    a["bucket"] = (a.K_nq / bucket).round() * bucket
    near = a[(a.bucket > nq_level * (1 - band)) & (a.bucket < nq_level * (1 + band))]
    cw = near[near.call & (near.bucket >= nq_level)].groupby("bucket").dg.sum()
    pw = near[~near.call & (near.bucket <= nq_level)].groupby("bucket").dg.sum()
    call_wall = float(cw.idxmax()) if len(cw) else float("nan")
    put_wall = float(pw.idxmin()) if len(pw) else float("nan")
    # gamma flip: re-price total dealer gamma at hypothetical NQ levels
    grid = np.linspace(nq_level * (1 - band), nq_level * (1 + band), 61)
    tot = []
    for L in grid:
        Sx = a.S.values * L / nq_level
        g = _bs_gamma(Sx, a.K.values, a.tt.values, a.iv.values)
        tot.append(float((sign * g * a.oi.values * 100 * Sx ** 2 * 0.01).sum()))
    tot = np.array(tot)
    flip = float("nan")
    for i in range(1, len(grid)):
        if tot[i - 1] * tot[i] < 0:
            w = abs(tot[i - 1]) / (abs(tot[i - 1]) + abs(tot[i]))
            cand = grid[i - 1] + (grid[i] - grid[i - 1]) * w
            if np.isnan(flip) or abs(cand - nq_level) < abs(flip - nq_level):
                flip = cand
    return {"call_wall": call_wall, "put_wall": put_wall, "flip": flip,
            "above_flip": (nq_level > flip) if np.isfinite(flip) else None}


def wall_lines(w, nq_level, qqq_per_nq=None):
    if not w:
        return ["  gamma walls: n/a"]
    f = lambda v: f"{v:,.0f}" if np.isfinite(v) else "n/a"
    side = ("NQ is ABOVE the flip (dealers dampen moves)" if w["above_flip"] else
            "NQ is BELOW the flip (dealers amplify moves)" if w["above_flip"] is not None else "")
    q = (lambda v: f"{v * qqq_per_nq:,.0f}" if np.isfinite(v) else "n/a") if qqq_per_nq else None
    return [f"  NQ futures prices: Call wall {f(w['call_wall'])} | Put wall {f(w['put_wall'])} | Gamma flip {f(w['flip'])}",
            (f"  (from QQQ + NDX options; in QQQ terms ~{q(w['call_wall'])} / {q(w['put_wall'])} / {q(w['flip'])})" if q else ""),
            f"  {side}" if side else "",
            "  Tested 2014-25: walls are NOT support/resistance (no better than random levels).",
            "  If the put wall breaks, drops tended to run a bit further. Below the flip = bigger days."]


# ------------------------------------------------------------------ earnings implied moves
def fetch_chain(sym, timeout=240):
    url = f"https://cdn-api.cboe.com/api/global/delayed_quotes/options/{sym}.json"
    body = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    return json.loads(body)


def earnings_move(sym, report_day, when, ts):
    """Implied move around a report. report_day: date; when: 'before open'/'after close'."""
    import ndx as _ndx
    t, d = _ndx.parse(fetch_chain(sym), roots=(sym,))
    S = _ndx.spot_by_parity(d)
    if not np.isfinite(S):
        return None
    rd = pd.Timestamp(report_day)
    eff = rd if when == "before open" else rd + pd.offsets.BDay(1)   # first session that reacts
    r = atm_straddle(d, S, min_dte=0, expiry_on_or_after=eff)
    if r is None:
        return None
    e, strad, _ = r
    days = _tdays(pd.Timestamp(ts), e)
    return {"sym": sym, "when": when, "move_pct": strad / S * 100, "days": days,
            "expiry": e.date(), "spot": S}


def earnings_lines(moves):
    out = []
    for m in moves:
        span = "" if m["days"] <= 1 else f" (option covers {m['days']} sessions, so a bit wider than the report alone)"
        out.append(f"  {m['sym']} reports {m['when']}: options price a ±{m['move_pct']:.1f}% move{span}")
    return out
