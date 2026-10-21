"""
strategy_lab.py - Volta's strategy lab. Complete intraday NQ strategies (entry, filter, stop, target, time exit),
written as small JSON specs - never free code - and backtested on 1-minute NQ 2014-2026 with pessimistic fills.

Spec:
{"name": "...",
 "entry":  {"type": "level", "level": "<LEVEL>", "action": "fade|break", "window": ["08:30", "11:00"]}
        or {"type": "time", "at": "09:00", "side": "long|short|<formula: > 0 long, < 0 short>"},
 "filter": "<formula over known columns, trade only when > 0>"   (optional),
 "stop":   {"points": 15} or {"range": 0.25}    (fraction of the options-based expected day range),
 "target": {"R": 4} or {"points": 40} or {"level": "<LEVEL>"},
 "exit":   "14:55"}                               (Chicago time, flat by then)
fade = limit order AT the level against the approach (level above price -> sell it, below -> buy it);
break = stop order through the level (level above -> buy the break, below -> sell the break).

Fills (deliberately pessimistic): limit entries/targets need price to trade 1 tick THROUGH the level; stop entries and
stop exits pay 1 tick slippage; if stop and target are both inside one bar, the stop counts; no target on the fill bar;
commission 0.25 pt per round trip. Results in NQ points and in R (multiples of the stop).
Harsh fills (since 2026-10-21, HARSH=True; env STRAT_HARSH=0 only for before/after comparisons): stop exits and stop
(break) entries slip MORE where reality is harsher - +1 tick per 50% the session's range exceeds its expected range
(max +6), +1 on red-folder news days, +2 on FOMC days, +2 for crude oil on Wednesdays (EIA inventory report). These
extra ticks are model assumptions (no fill data), deliberately on the pessimistic side.

Guardrails before anything is called a strategy:
 1. In-sample 2014-2023 only: >= 150 trades, positive after costs, positive in >= 70% of years.
 2. Placebo: the same stop/target/side entered at random minutes on the same days (100x) - must beat it (p < 0.05).
 3. Stress: stop and target nudged -20%/+20%, window +-30 min, costs doubled - must stay positive.
 4. Locked exam: 2024-2026 data, never used while searching, max 10 exams per week (counted publicly).
"""
import hashlib, json, os, re, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
TICK, COMM, EXAM_FROM, EXAMS_PER_WEEK = 0.25, 0.25, "2024-01-01", 2   # 2/week since 21 Oct 2026: every look at 2024-26 leaks (reusable-holdout problem)
HARSH = os.environ.get("STRAT_HARSH", "1") != "0"
SLIP_RANGE_STEP, SLIP_RANGE_MAX, SLIP_RED, SLIP_FOMC, SLIP_CL_WED = 0.5, 6, 1, 2, 2
LOG, EXAMS = os.path.join(K, "strategies.jsonl"), os.path.join(K, "strategy_exams.json")
STATIC = ["open", "yday_high", "yday_low", "yday_close", "yday_mid", "asia_high", "asia_low", "london_high", "london_low",
          "on_high", "on_low", "midnight_open", "or15_high", "or15_low"]
DYNAMIC = ["vwap", "vwap_up1", "vwap_dn1", "vwap_up2", "vwap_dn2"]
STATIC += ["pivot", "r1", "s1", "r2", "s2", "exp50_up", "exp50_dn", "exp70_up", "exp70_dn", "exp90_up", "exp90_dn",
           "atr10_up", "atr10_dn", "atr15_up", "atr15_dn", "atr20_up", "atr20_dn", "atr25_up", "atr25_dn", "atr30_up", "atr30_dn",
           "ewma1_up", "ewma1_dn", "ewma2_up", "ewma2_dn"]
LEVELS = STATIC + DYNAMIC
LEVEL_HELP = ("open (NY open 08:30 CT), yday_high/yday_low/yday_close/yday_mid (yesterday's NY session), asia_high/asia_low "
              "(18:00-02:00 CT), london_high/london_low (02:00-07:00 CT), on_high/on_low (whole overnight), midnight_open "
              "(00:00 New York), or15_high/or15_low (first 15 minutes, usable from 08:45), pivot/r1/s1/r2/s2 (classic floor "
              "pivots from yesterday), exp50_up/exp50_dn/exp70_up/exp70_dn/exp90_up/exp90_dn (open +- 50/70/90% of Volta's expected "
              "day range: exhaustion levels), atr10/atr15/atr20/atr25/atr30 _up/_dn (open +- 1-3x the 14-day ATR), "
              "ewma1/ewma2 _up/_dn (yesterday's close +- 1/2 EWMA-0.94 daily sigmas), vwap and its 1/2 standard-deviation "
              "bands vwap_up1/vwap_dn1/vwap_up2/vwap_dn2 (anchored at midnight New York)")


class Bad(Exception):
    pass


_DATA = {}


MARKETS = {  # tick, round-trip cost in points, $ per point for the MICRO contract (prop accounts trade micros)
    "NQ": {"tick": 0.25, "comm": 0.25, "pv": 2.0, "micro": "MNQ"},
    "GC": {"tick": 0.10, "comm": 0.10, "pv": 10.0, "micro": "MGC"},
    "CL": {"tick": 0.01, "comm": 0.01, "pv": 100.0, "micro": "MCL"}}


def data(market="NQ"):
    market = (market or "NQ").upper()
    if market != "NQ":
        if market not in _MK:
            z = np.load(os.path.join(K, f"strat_bars_{market.lower()}.npz"))
            D = {k: z[k].astype(np.float64) for k in ("O", "H", "L", "C", "V")}
            M = pd.read_csv(os.path.join(K, f"strat_sessions_{market.lower()}.csv"))
            M["yday_mid"] = (M.yday_high + M.yday_low) / 2
            _add_vol_cols(D, M); _add_slip_cols(M, market); M.attrs["pv"] = MARKETS[market]["pv"]; D["M"] = M; D.update(MARKETS[market]); D["market"] = market
            _MK[market] = D
        return _MK[market]
    if not _DATA:
        z = np.load(os.path.join(K, "strat_bars.npz"))
        _DATA.update({k: z[k].astype(np.float64) for k in ("O", "H", "L", "C", "V")})
        _DATA.update(MARKETS["NQ"]); _DATA["market"] = "NQ"
        M = pd.read_csv(os.path.join(K, "strat_sessions.csv"))
        M["yday_mid"] = (M.yday_high + M.yday_low) / 2
        _add_vol_cols(_DATA, M); _add_slip_cols(M, "NQ"); M.attrs["pv"] = 2.0
        _DATA["M"] = M
    return _DATA


_MK = {}


def _add_vol_cols(D, M):
    """ATR (14 sessions, past only) and EWMA volatility (lambda 0.94, close-to-close, known before each session)."""
    C = D["C"][:, -1]; rng_ = D["H"].max(1) - D["L"].min(1)
    M["atr14"] = pd.Series(rng_).shift(1).rolling(14, min_periods=5).mean().values
    r = pd.Series(np.log(C)).diff()
    var = np.full(len(r), np.nan); v = np.nanvar(r.values[1:60]) if len(r) > 60 else 1e-4
    for j in range(1, len(r)):
        var[j] = v
        if np.isfinite(r.iloc[j]): v = 0.94 * v + 0.06 * r.iloc[j] ** 2
    M["ewma_sd"] = np.sqrt(var)


def _add_slip_cols(M, market):
    """Extra stop slippage (ticks) known per session from the calendar: red-folder news, FOMC, crude-oil Wednesdays."""
    x = np.zeros(len(M))
    st = os.path.join(K, "session_table.csv")
    if os.path.exists(st):
        Q = pd.read_csv(st, usecols=lambda c: c in ("session", "k_red_any", "k_fomc_day")).drop_duplicates("session").set_index("session")
        q = Q.reindex(M.session.values)
        x += SLIP_RED * (q.get("k_red_any", pd.Series(0, index=q.index)).fillna(0).values > 0.5)
        x += SLIP_FOMC * (q.get("k_fomc_day", pd.Series(0, index=q.index)).fillna(0).values > 0.5)
    if market == "CL":
        x += SLIP_CL_WED * (pd.to_datetime(M.session).dt.weekday.values == 2)
    M["slip_news"] = x


def slip_ticks(D, i, M=None):
    """Ticks a stop order pays in session i: 1 normally; more on fast (range above expected) and news days if HARSH."""
    if not HARSH: return 1.0
    M = D["M"].iloc[i] if M is None else M
    O = D["O"][i]; rng_ = float(np.nanmax(D["H"][i]) - np.nanmin(D["L"][i])); exp_ = float(M.get("fc_frac", np.nan)) * float(O[0])
    x = min(max(np.floor((rng_ / exp_ - 1) / SLIP_RANGE_STEP), 0), SLIP_RANGE_MAX) if np.isfinite(exp_) and exp_ > 0 else 0.0
    news = M.get("slip_news", 0.0)
    return 1.0 + x + (float(news) if np.isfinite(news) else 0.0)


def mins(hhmm):
    h, m = map(int, str(hhmm).split(":")); return h * 60 + m - 510          # bar index from 08:30 CT


def vwap_paths(D, i):
    """VWAP and sigma known BEFORE each bar (anchored at midnight New York), shape (390,)."""
    M = D["M"].iloc[i]; H, L, C, V = D["H"][i], D["L"][i], D["C"][i], D["V"][i]
    tp = (H + L + C) / 3
    pv = M.vw_pv + np.concatenate([[0], np.cumsum(tp * V)[:-1]]); v = M.vw_v + np.concatenate([[0], np.cumsum(V)[:-1]])
    pv2 = M.vw_pv2 + np.concatenate([[0], np.cumsum(tp * tp * V)[:-1]])
    vw = pv / np.maximum(v, 1); sd = np.sqrt(np.maximum(pv2 / np.maximum(v, 1) - vw * vw, 0))
    return vw, sd


def level_path(D, i, name):
    M = D["M"].iloc[i]
    if name in DYNAMIC:
        vw, sd = vwap_paths(D, i)
        k = {"vwap": 0, "vwap_up1": 1, "vwap_dn1": -1, "vwap_up2": 2, "vwap_dn2": -2}[name]
        return vw + k * sd
    if name in ("or15_high", "or15_low"):
        h, l = D["H"][i][:15].max(), D["L"][i][:15].min()
        p = np.full(390, np.nan); p[15:] = h if name == "or15_high" else l; return p
    if name == "open": return np.full(390, D["O"][i][0])
    if name in ("pivot", "r1", "s1", "r2", "s2"):                       # classic floor pivots from yesterday's NY session
        yh, yl, yc = (float(M.get(k, np.nan)) for k in ("yday_high", "yday_low", "yday_close"))
        P = (yh + yl + yc) / 3
        v = {"pivot": P, "r1": 2 * P - yl, "s1": 2 * P - yh, "r2": P + (yh - yl), "s2": P - (yh - yl)}[name]
        return np.full(390, v)
    if name.startswith("atr"):                                            # open +- 1/1.5/2/2.5/3 x the 14-session ATR
        k = int(name[3:5]) / 10; a = float(M.get("atr14", np.nan))
        return np.full(390, D["O"][i][0] + (k if name.endswith("up") else -k) * a)
    if name.startswith("ewma"):                                           # yesterday's close +- 1/2 EWMA(0.94) daily sigmas
        k = int(name[4]); c = float(M.get("yday_close", np.nan)); sd = float(M.get("ewma_sd", np.nan))
        return np.full(390, c * (1 + (k if name.endswith("up") else -k) * sd))
    if name.startswith("exp"):                                            # exhaustion levels: open +- 50/70/90% of the brain's expected range
        k = int(name[3:5]) / 100; R = float(M.get("fc_frac", np.nan)) * D["O"][i][0]
        return np.full(390, D["O"][i][0] + (k if name.endswith("up") else -k) * R)
    v = M.get(name, np.nan)
    return np.full(390, float(v) if pd.notna(v) else np.nan)


def validate(spec):
    if not isinstance(spec, dict): raise Bad("spec must be an object")
    if (spec.get("market") or "NQ").upper() not in MARKETS: raise Bad(f"market must be one of {', '.join(MARKETS)}")
    e = spec.get("entry") or {}
    if e.get("type") not in ("level", "time"): raise Bad("entry.type must be level or time")
    if e["type"] == "level":
        if e.get("level") not in LEVELS: raise Bad(f"unknown level '{e.get('level')}' (use one of {', '.join(LEVELS)})")
        if e.get("action") not in ("fade", "break"): raise Bad("entry.action must be fade or break")
        w = e.get("window") or ["08:30", "11:00"]
        if not (0 <= mins(w[0]) < mins(w[1]) <= 385): raise Bad("window must be within 08:30-14:55")
    else:
        if not (0 <= mins(e.get("at", "")) <= 380): raise Bad("entry.at must be 08:30-14:50")
        sd = str(e.get("side", "long"))
        if sd.startswith("own:") and sd[4:].lstrip("-") not in ("gap", "mid", "pos", "day"): raise Bad("own: side must be gap, mid, pos or day")
    st, tg = spec.get("stop") or {}, spec.get("target") or {}
    if not (("points" in st and 2 <= float(st["points"]) <= 200) or ("range" in st and 0.03 <= float(st["range"]) <= 1.5)):
        raise Bad("stop must be {points: 2-200} or {range: 0.03-1.5}")
    if not (("R" in tg and 0.3 <= float(tg["R"]) <= 15) or ("points" in tg and 2 <= float(tg["points"]) <= 600) or tg.get("level") in LEVELS):
        raise Bad("target must be {R: 0.3-15}, {points: 2-600} or {level: <LEVEL>}")
    ex = spec.get("exit", "14:55")
    if not (1 <= mins(ex) <= 389): raise Bad("exit must be 08:31-14:59")       # up to the cash close (since 21 Oct 2026)
    mg = spec.get("manage")
    if mg is not None:
        if not isinstance(mg, dict) or not set(mg) <= {"be_at_R", "trail_R", "partial"}: raise Bad("manage may only have be_at_R, trail_R, partial")
        for k_ in ("be_at_R", "trail_R"):
            if k_ in mg and not (0.25 <= float(mg[k_]) <= 5): raise Bad(f"manage.{k_} must be 0.25-5")
        if "partial" in mg and not (0.25 <= float(mg["partial"].get("at_R", 0)) <= 5 and 0.1 <= float(mg["partial"].get("frac", 0.5)) <= 0.9):
            raise Bad("manage.partial must be {at_R: 0.25-5, frac: 0.1-0.9}")
    return True


def _filters(spec, X):
    """Per-session trade side/filter arrays from formulas over known columns (leak-guarded by the engine)."""
    import test_engine as T
    D = data(spec.get("market")); M = D["M"]; n = len(M); dates = pd.to_datetime(M.date)
    allow = np.ones(n, bool); side = np.zeros(n)
    if spec.get("filter"):
        f = T.evaluate(spec["filter"], X); allow = (f.reindex(dates).values > 0)
    e = spec["entry"]
    if e["type"] == "time":
        sd = e.get("side", "long")
        if sd in ("long", "short"): side[:] = 1 if sd == "long" else -1
        elif sd.lstrip("own:-") == "day" and sd.startswith("own:"):   # direction of the session so far: decided AT the entry minute
            side[:] = 2 if not sd[4:].startswith("-") else -2               # (marker; simulate_session resolves it from the bars)
        elif sd.startswith("own:"):                            # direction from THIS market's own pre-open moves
            k = sd[4:]; neg = k.startswith("-"); k = k.lstrip("-")
            v = {"gap": M.open - M.yday_close, "mid": M.open - M.midnight_open,
                 "pos": (M.open - M.on_low) / (M.on_high - M.on_low).replace(0, np.nan) - 0.5}[k].values
            side = np.sign(np.nan_to_num(v)) * (-1 if neg else 1)
        else:
            s = T.evaluate(sd, X).reindex(dates).values; side = np.sign(np.nan_to_num(s))
    return allow, side


def simulate_session(D, i, spec, side=0, entry_override=None, cost_mult=1.0, stop_mult=1.0, tgt_mult=1.0, win_shift=0):
    """One session -> (pnl points, R, side) or None if no trade."""
    O, H, L, C = D["O"][i], D["H"][i], D["L"][i], D["C"][i]; M = D["M"].iloc[i]
    tk, cm = D.get("tick", TICK), D.get("comm", COMM)
    sl = slip_ticks(D, i, M) * tk                                      # stop-order slippage (points) this session
    e = spec["entry"]; xe = min(mins(spec.get("exit", "14:55")), 389)
    st = spec["stop"]
    stop_pts = float(st["points"]) if "points" in st else float(st["range"]) * float(M.fc_frac) * O[0]
    if not np.isfinite(stop_pts): return None
    stop_pts = max(round(stop_pts * stop_mult / tk) * tk, 8 * tk)
    if entry_override is not None:                                     # placebo: market entry at a random minute
        k, s = entry_override
        ep = O[k] + s * tk
    elif e["type"] == "time":
        k = mins(e["at"]); s = side
        if abs(s) == 2:                                                # own:day - sign of (last close before entry - session open)
            mv = C[k - 1] - O[0] if k >= 1 else 0.0
            s = int(np.sign(mv)) * (1 if s > 0 else -1)
        if s == 0: return None
        ep = O[k] + s * tk
    else:
        w0 = max(mins(e.get("window", ["08:30"])[0]), 0); w1 = min(mins(e.get("window", ["08:30", "11:00"])[1]) + win_shift, xe - 1)
        lv = level_path(D, i, e["level"])
        if e["level"] in ("or15_high", "or15_low"): w0 = max(w0, 15)
        if w1 <= w0 or not np.isfinite(lv[w0]): return None
        ref = O[w0] if w0 == 0 else C[w0 - 1]
        above = lv[w0] > ref
        if abs(lv[w0] - ref) < tk: return None
        if e["action"] == "fade":
            s = -1 if above else 1
            hit = (H[w0:w1 + 1] >= lv[w0:w1 + 1] + tk) if above else (L[w0:w1 + 1] <= lv[w0:w1 + 1] - tk)
        else:
            s = 1 if above else -1
            hit = (H[w0:w1 + 1] >= lv[w0:w1 + 1] + tk) if above else (L[w0:w1 + 1] <= lv[w0:w1 + 1] - tk)
        if not hit.any(): return None
        k = w0 + int(np.argmax(hit)); lvl = lv[k]
        conf = e.get("confluence")                                    # only trade if another level sits close by
        if conf:
            near = [abs(level_path(D, i, c)[k] - lvl) for c in conf.get("levels", []) if c != e["level"] and c in LEVELS]
            if not any(np.isfinite(x) and x <= float(conf.get("within", 10)) for x in near): return None
        ep = lvl if e["action"] == "fade" else lvl + s * (tk + sl)       # break = stop order: 1 tick through + slippage
    if k >= xe: return None
    stop = ep - s * stop_pts
    tg = spec["target"]
    if "R" in tg: tgt = ep + s * float(tg["R"]) * tgt_mult * stop_pts
    elif "points" in tg: tgt = ep + s * float(tg["points"]) * tgt_mult
    else:
        tl = level_path(D, i, tg["level"])[k]
        if not np.isfinite(tl) or (tl - ep) * s <= 2 * tk: return None
        tgt = tl
    # fill bar: only the stop can hit (pessimistic)
    mg = spec.get("manage")
    if (s == 1 and L[k] <= stop) or (s == -1 and H[k] >= stop):
        xp = stop - s * sl
    elif mg:                                                           # trade management: bar by bar, pessimistic, no lookahead
        cur, best, rem, got = stop, ep, 1.0, 0.0
        be, tr, part = mg.get("be_at_R"), mg.get("trail_R"), mg.get("partial")
        for j in range(k + 1, xe):
            if (s == 1 and L[j] <= cur) or (s == -1 and H[j] >= cur):  # stop (or moved stop) first within a bar
                got += rem * ((cur - s * sl) - ep) * s; rem = 0.0; break
            if part and rem == 1.0:
                pl = ep + s * float(part["at_R"]) * stop_pts
                if (s == 1 and H[j] >= pl + tk) or (s == -1 and L[j] <= pl - tk):
                    f = float(part.get("frac", 0.5)); got += f * (pl - ep) * s; rem -= f
            if (s == 1 and H[j] >= tgt + tk) or (s == -1 and L[j] <= tgt - tk):
                got += rem * (tgt - ep) * s; rem = 0.0; break
            best = max(best, H[j]) if s == 1 else min(best, L[j]); fav = (best - ep) * s
            if be is not None and fav >= float(be) * stop_pts:         # move the stop to breakeven (applies from the next bar)
                cur = max(cur, ep) if s == 1 else min(cur, ep)
            if tr is not None and fav >= float(tr) * stop_pts:         # trail the stop tr*R behind the best price so far
                ts = best - s * float(tr) * stop_pts; cur = max(cur, ts) if s == 1 else min(cur, ts)
        if rem > 0: got += rem * ((O[xe] - s * tk) - ep) * s           # time exit for whatever is left
        pnl = got - cm * cost_mult
        return pnl, pnl / stop_pts, s, k
    else:
        j0, j1 = k + 1, xe
        if j0 >= j1:
            xp = O[xe] - s * tk
        else:
            hs = (L[j0:j1] <= stop) if s == 1 else (H[j0:j1] >= stop)
            ht = (H[j0:j1] >= tgt + tk) if s == 1 else (L[j0:j1] <= tgt - tk)
            a = int(np.argmax(hs)) if hs.any() else 10 ** 6; b = int(np.argmax(ht)) if ht.any() else 10 ** 6
            if a == b == 10 ** 6: xp = O[xe] - s * tk                   # time exit at the exit bar's open
            elif a <= b: xp = stop - s * sl                             # stop first (or same bar)
            else: xp = tgt
    pnl = (xp - ep) * s - cm * cost_mult
    return pnl, pnl / stop_pts, s, k


def backtest(spec, X, sessions=None, **kw):
    D = data(spec.get("market")); M = D["M"]
    allow, side = _filters(spec, X)
    idx = np.arange(len(M)) if sessions is None else sessions
    rows = []
    for i in idx:
        if not allow[i]: continue
        r = simulate_session(D, i, spec, side=side[i], **kw)
        if r: rows.append((M.session.iloc[i], i, r[0], r[1], r[2], r[3]))
    return pd.DataFrame(rows, columns=["session", "i", "pnl", "R", "side", "k"])


def metrics(T):
    if not len(T): return {"n": 0}
    yrs = T.groupby(T.session.str[:4]).R.mean()
    eq = T.R.cumsum(); dd = float((eq - eq.cummax()).min())
    gp, gl = T.pnl[T.pnl > 0].sum(), -T.pnl[T.pnl < 0].sum()
    return {"n": int(len(T)), "win": round(float((T.pnl > 0).mean()), 3), "avg_R": round(float(T.R.mean()), 3),
            "avg_pts": round(float(T.pnl.mean()), 2), "pf": round(float(gp / gl), 2) if gl > 0 else None, "max_dd_R": round(dd, 1),
            "years_pos": f"{int((yrs > 0).sum())}/{len(yrs)}", "per_year": round(len(T) / max(T.session.str[:4].nunique(), 1), 1)}


def placebo(spec, T, reps=100, seed=7):
    """Same days, same side, same stop/target and exit - but entered at a random minute instead of the strategy's entry."""
    D = data(spec.get("market")); rng = np.random.default_rng(seed); e = spec["entry"]
    lo = mins(e["window"][0]) if e["type"] == "level" else 1
    hi = mins(e["window"][1]) if e["type"] == "level" else min(mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2)
    means = []
    for _ in range(reps):
        Rs = []
        for i, s in zip(T.i.values, T.side.values):
            r = simulate_session(D, int(i), spec, entry_override=(int(rng.integers(lo, hi)), int(s)))
            if r: Rs.append(r[1])
        means.append(np.mean(Rs) if Rs else 0.0)
    return np.array(means)


def _week():
    d = datetime.now(timezone.utc).isocalendar(); return f"{d[0]}-W{d[1]:02d}"


def _prop_inputs(T, M):
    """Day-by-day inputs for prop_sim: result per micro (MNQ points), the day's worst point and the median stop (sizing).
    The worst point is THAT trade's own stop (range stops are wider on volatile days) or its actual loss if larger
    (slippage) - not the median stop, so a wide-stop day can blow the account when the real trade would have."""
    ses = M.session.values; ses = ses[(ses >= T.session.min()) & (ses <= T.session.max())] if len(T) else ses
    pv = float(M.attrs.get("pv", 2.0)) if hasattr(M, "attrs") else 2.0
    eq = T.pnl.values * pv / 2.0                                       # dollars per micro, expressed in MNQ points ($2/pt)
    pts = pd.Series(0.0, index=ses); pts[T.session.values] = eq
    neg = np.abs(eq[eq < 0])
    stop = float(np.median(neg)) if len(neg) else 20.0
    R = T.R.values if "R" in T else np.zeros(len(T))
    own = np.where(np.abs(R) > 1e-9, np.abs(eq / np.where(np.abs(R) > 1e-9, R, 1.0)), stop)   # this trade's stop (pnl / R)
    wst = pd.Series(0.0, index=ses); wst[T.session.values] = -np.maximum(own, np.maximum(-eq, 0.0))
    return pts.values, np.where(pts.values != 0, np.minimum(wst.values, -1e-9), 0.0), stop


def _sizer(spec, stop):
    """Sizing from the spec's optional "prop" block: {"risk": share of the buffer to the max loss risked per trade (default
    0.25), "eval_risk": override during the evaluation}. Contracts = floor(risk * buffer / (stop * $2 per MNQ point))."""
    import prop_sim
    pr = spec.get("prop") or {}; r = float(pr.get("risk", 0.25)); re_ = float(pr.get("eval_risk", r))
    r, re_ = min(max(r, 0.02), 0.9), min(max(re_, 0.02), 0.9)
    # account playbook (optional): "eval_finish": near the eval target, trade only as many micros as needed to reach it
    # (less risk exactly when one bad day would undo the progress); "funded_micros": a fixed small size once funded
    # (survive to the payouts instead of growing fast). Target R taken from the spec (1R if the target is a level/points).
    fin, fm = bool(pr.get("eval_finish")), pr.get("funded_micros")
    tg = spec.get("target") or {}; win_per = stop * prop_sim.MNQ * float(tg.get("R", 1.0))
    def size(phase, profit, buf, P=None):                     # never freeze: keep 1 micro while one stop still fits the buffer
        if phase != "eval" and fm: n = int(fm)
        else: n = int(((re_ if phase == "eval" else r) * buf) // (stop * prop_sim.MNQ))
        if phase == "eval" and fin and P is not None and win_per > 0:
            need = max(P["target"] - profit, 0.0); n = min(n, int(np.ceil(need / win_per)))
        return max(n, 1 if stop * prop_sim.MNQ < buf else 0)
    size.wants_plan = True
    return size


def farm_score(T, M, spec, plan, slots=5):
    """Monthly cash flow of running `slots` copy-traded accounts on `plan` (re-buying an eval whenever one ends)."""
    import prop_sim
    pts, worst, stop = _prop_inputs(T, M)
    ses = M.session.values; ses = ses[(ses >= T.session.min()) & (ses <= T.session.max())]
    return prop_sim.farm(pts, worst, ses, plan, _sizer(spec or {}, stop), slots=slots)


def prop_score(T, M, spec=None, plan=None, starts=None):
    """The mission metric: run the strategy's day-by-day results through every prop plan in knowledge/prop_firms.json
    (or one plan). Returns the results, best expected payout minus fee first."""
    import prop_sim
    pts, worst, stop = _prop_inputs(T, M)
    size = _sizer(spec or {}, stop)
    if plan: return [prop_sim.evaluate(pts, worst, plan, size, starts, step=4)]
    return prop_sim.best_plan(pts, worst, lambda P: size, starts)


def prop_path(spec, X, T, M, out, head):
    """Prop-mission protocol: positive EV after fees in both halves of 2014-2023 (checked before), beats random entries on
    the same days under the same rules, survives double costs, then the locked 2024-2026 exam must also pay out > fee."""
    import prop_sim
    best = out["prop"][0]; plan = best["plan"]
    D = data(spec.get("market")); rng = np.random.default_rng(11); e = spec["entry"]
    lo = mins(e["window"][0]) if e["type"] == "level" else 1
    hi = mins(e["window"][1]) if e["type"] == "level" else min(mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2)
    evs = []
    for _ in range(20):
        rows = []
        for s_, i, sd in zip(T.session.values, T.i.values, T.side.values):
            r = simulate_session(D, int(i), spec, entry_override=(int(rng.integers(lo, hi)), int(sd)))
            if r: rows.append((s_, i, r[0], r[1], r[2], r[3]))
        P = pd.DataFrame(rows, columns=["session", "i", "pnl", "R", "side", "k"])
        evs.append(prop_score(P, M, spec, plan)[0]["ev_per_eval"] if len(P) else -best["fee"])
    p = float((np.array(evs) >= best["ev_per_eval"]).mean()); out["prop_placebo"] = {"mean_ev": round(float(np.mean(evs)), 1), "p": p}
    if p >= 0.10:
        return f"NOT CONFIRMED (prop path): random entries on the same days pay about as much (random EV {np.mean(evs):+.0f}, p={p:.2f}). {head}"
    ins = np.where(M.session < EXAM_FROM)[0]
    T2 = backtest(spec, X, ins, cost_mult=2.0); ev2 = prop_score(T2, M, spec, plan)[0]["ev_per_eval"] if len(T2) else -1
    if ev2 <= 0:
        return f"NOT CONFIRMED (prop path): fragile - with double costs the EV per eval is {ev2:+.0f}. {head}"
    if out.get("source") not in EXAM_SOURCES:
        return f"PASSED IN-SAMPLE (prop path) - single ideas no longer take the locked exam (propose it as a family). {head}"
    ex = json.load(open(EXAMS)) if os.path.exists(EXAMS) else {}
    w = _week(); ex.setdefault(w, 0)
    if ex[w] >= EXAMS_PER_WEEK:
        return f"PASSED IN-SAMPLE (prop path), WAITING FOR EXAM (weekly exam budget used up). {head}"
    ex[w] += 1; json.dump(ex, open(EXAMS, "w"), indent=1)
    exam = np.where(M.session >= EXAM_FROM)[0]; E = backtest(spec, X, exam)
    pe = prop_score(E, M, spec, plan)[0] if len(E) >= 30 else {"ev_per_eval": -1, "pass_rate": 0, "avg_payout_per_eval": 0}
    out["prop_exam"] = pe
    txt = f"LOCKED EXAM 2024-2026 on {plan}: pass {pe['pass_rate']:.0%}, ${pe['avg_payout_per_eval']:.0f} paid out per eval, EV {pe['ev_per_eval']:+.0f}"
    if pe["ev_per_eval"] > 0:
        return f"PROMISING STRATEGY (prop path, passed the locked exam): {txt}. {head}; beats random entries (p={p:.2f}), survives double costs"
    return f"NOT CONFIRMED - failed the locked exam (prop path): {txt}. {head}"


def evaluate(spec, X, source="engine", name=None):
    """Full protocol. Returns (verdict, how)."""
    validate(spec)
    D = data(spec.get("market")); M = D["M"]
    ins = np.where(M.session < EXAM_FROM)[0]; exam = np.where(M.session >= EXAM_FROM)[0]
    T = backtest(spec, X, ins); m = metrics(T)
    label = spec.get("name") or name or "strategy"
    head = (f"in-sample 2014-2023: {m.get('n', 0)} trades, win {m.get('win', 0):.0%}, avg {m.get('avg_R', 0):+.2f}R "
            f"({m.get('avg_pts', 0):+.1f} pts/trade after costs), PF {m.get('pf')}, positive in {m.get('years_pos', '0/0')} years, "
            f"max drawdown {m.get('max_dd_R', 0)}R") if m.get("n") else "in-sample: no trades"
    PROP_NOTE = ""
    out = {"date": datetime.now(timezone.utc).date().isoformat(), "name": label, "spec": spec, "source": source, "insample": m}
    head_prop, prop_ok = "", False
    try:                                                      # the mission metric: payouts minus fee per prop evaluation
        PS = prop_score(T, M, spec); best = PS[0]; out["prop"] = PS
        half = [prop_score(T[T.session.str[:4].astype(int) <= 2018], M, spec, best["plan"])[0],
                prop_score(T[T.session.str[:4].astype(int) >= 2019], M, spec, best["plan"])[0]]
        out["prop_halves"] = half
        prop_ok = best["ev_per_eval"] > 0 and all(h["ev_per_eval"] > 0 for h in half)
        head_prop = (f" | PROP SIM best plan {best['plan']}: pass {best['pass_rate']:.0%}, ${best['avg_payout_per_eval']:.0f} paid out "
                     f"per eval, EV after the ${best['fee']} fee {best['ev_per_eval']:+.0f} (2014-18 {half[0]['ev_per_eval']:+.0f}, "
                     f"2019-23 {half[1]['ev_per_eval']:+.0f})")
    except Exception as e:
        head_prop = f" | prop sim failed: {type(e).__name__}"
    def done(verdict):
        out["verdict"] = verdict + head_prop
        if verdict.startswith("PROMISING STRATEGY"):          # immediate review (no waiting for Sunday): luck, stability, nudges, costs
            try:
                import review_prop
                lab, why, det = review_prop.review(spec, X, (out.get("prop_exam") or (out.get("prop") or [{}])[0]).get("plan"))
                out["review"] = f"{lab} (auto, {datetime.now(timezone.utc):%Y-%m-%d}): {why}"; out["review_detail"] = det
            except Exception as e:
                print("auto review failed:", type(e).__name__, e)
        with open(LOG, "a") as f: f.write(json.dumps(out) + "\n")
        return out["verdict"], f"strategy lab: {json.dumps(spec)[:300]}"
    if m.get("n", 0) < 150:
        return done(f"NOT CONFIRMED on my data: too few trades ({m.get('n', 0)} in 2014-2023, need 150). {head}")
    yp, yt = map(int, m["years_pos"].split("/"))
    if m["avg_R"] <= 0 or yp < 0.7 * yt:
        if prop_ok:                                           # the mission path: pays out under prop rules even without a big R edge
            return done(prop_path(spec, X, T, M, out, head))
        return done(f"NOT CONFIRMED on my data: {head}")
    pl = placebo(spec, T); p = float((pl >= m["avg_R"]).mean()); out["placebo"] = {"mean_R": round(float(pl.mean()), 3), "p": p}
    if p >= 0.05:
        return done(f"NOT CONFIRMED on my data: no better than random entries with the same stop/target "
                    f"(random {pl.mean():+.2f}R, p={p:.2f}). {head}")
    nudges = [dict(stop_mult=0.8), dict(stop_mult=1.2), dict(tgt_mult=0.8), dict(tgt_mult=1.2), dict(cost_mult=2.0)]
    if spec["entry"]["type"] == "level": nudges += [dict(win_shift=-30), dict(win_shift=30)]
    nr = [metrics(backtest(spec, X, ins, **kw)).get("avg_R", -1) for kw in nudges]
    out["stress"] = nr
    if sum(r > 0 for r in nr) < 0.75 * len(nr) or nr[4] <= 0:
        return done(f"NOT CONFIRMED after the stress test (fragile: nudged/double-cost results {', '.join(f'{r:+.2f}R' for r in nr)}). {head}")
    if source not in EXAM_SOURCES:
        return done(f"PASSED IN-SAMPLE - single ideas no longer take the locked exam (propose it as a family). {head}; beats random entries (p={p:.2f})")
    ex = json.load(open(EXAMS)) if os.path.exists(EXAMS) else {}
    w = _week(); ex.setdefault(w, 0)
    if ex[w] >= EXAMS_PER_WEEK:
        return done(f"PASSED IN-SAMPLE, WAITING FOR EXAM (weekly exam budget used up). {head}; beats random entries (p={p:.2f})")
    ex[w] += 1; json.dump(ex, open(EXAMS, "w"), indent=1)
    E = backtest(spec, X, exam); me = metrics(E); out["exam"] = me
    total = sum(ex.values())
    exam_txt = (f"LOCKED EXAM 2024-2026: {me.get('n', 0)} trades, win {me.get('win', 0):.0%}, avg {me.get('avg_R', 0):+.2f}R "
                f"({me.get('avg_pts', 0):+.1f} pts), PF {me.get('pf')} [exam #{total} taken overall]")
    if me.get("n", 0) >= 30 and me["avg_R"] > 0 and me["avg_R"] >= m["avg_R"] / 3:
        return done(f"PROMISING STRATEGY (passed the locked exam): {exam_txt}. {head}; beats random entries (p={p:.2f}), survived stress")
    return done(f"NOT CONFIRMED - failed the locked exam: {exam_txt}. {head}")


EXAM_SOURCES = ("prop-search", "family")             # only the systematic search / registered families spend exams


def spec_id(spec):
    return hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]


SPEC_HELP = f"""{{"kind": "strategy", "name": "<short name>", "market": "NQ|GC|CL" (default NQ; GC = gold, CL = crude oil - use range stops there),
   "entry": {{"type": "level", "level": "<LEVEL>", "action": "fade|break", "window": ["08:30", "11:00"],
             "confluence": {{"levels": ["<LEVEL>", "..."], "within": 10}}}}   (confluence optional: trade only if one of
             those levels is within N points of the entry level at the touch)
         or {{"type": "time", "at": "09:00", "side": "long|short|<formula: > 0 long, < 0 short>|own:gap|own:-gap|own:mid|own:-mid|own:pos|own:-pos"}},
         (own:* = direction from the traded market's own gap / move since midnight / side of its overnight range; "-" = against it)
   "filter": "<optional formula over known columns; trade only when > 0>",
   "stop": {{"points": 15}} or {{"range": 0.25}},   "target": {{"R": 3}} or {{"points": 40}} or {{"level": "<LEVEL>"}},
   "exit": "14:55", "prop": {{"risk": 0.25, "eval_risk": 0.4}}, "explain": "<one line>"}}
   (prop = optional sizing for prop accounts: share of the buffer to the max-loss floor risked per trade, funded / eval)
   (A COMPLETE intraday NQ strategy, backtested on 1-minute data 2014-2023 with pessimistic fills and costs, then a
   locked 2024-2026 exam. fade = limit order at the level against the approach; break = stop order through it.
   stop range = fraction of the options-implied day range. LEVELS: {LEVEL_HELP}.
   Filters may use Volta's power probabilities pw_takes_pdh, pw_takes_pdl, pw_gap_fill, pw_tail_day (0-1, known at the
   open), k_ columns, gex_rank, iv30, vix, vix_curve, nq_vs_es etc. Never y_ columns.)"""
