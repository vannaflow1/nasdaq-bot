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
TICK, COMM, EXAM_FROM, EXAMS_PER_WEEK = 0.25, 0.25, "2024-01-01", 10
LOG, EXAMS = os.path.join(K, "strategies.jsonl"), os.path.join(K, "strategy_exams.json")
STATIC = ["open", "yday_high", "yday_low", "yday_close", "yday_mid", "asia_high", "asia_low", "london_high", "london_low",
          "on_high", "on_low", "midnight_open", "or15_high", "or15_low"]
DYNAMIC = ["vwap", "vwap_up1", "vwap_dn1", "vwap_up2", "vwap_dn2"]
LEVELS = STATIC + DYNAMIC
LEVEL_HELP = ("open (NY open 08:30 CT), yday_high/yday_low/yday_close/yday_mid (yesterday's NY session), asia_high/asia_low "
              "(18:00-02:00 CT), london_high/london_low (02:00-07:00 CT), on_high/on_low (whole overnight), midnight_open "
              "(00:00 New York), or15_high/or15_low (first 15 minutes, usable from 08:45), vwap and its 1/2 standard-deviation "
              "bands vwap_up1/vwap_dn1/vwap_up2/vwap_dn2 (anchored at midnight New York)")


class Bad(Exception):
    pass


_DATA = {}


def data():
    if not _DATA:
        z = np.load(os.path.join(K, "strat_bars.npz"))
        _DATA.update({k: z[k].astype(np.float64) for k in ("O", "H", "L", "C", "V")})
        M = pd.read_csv(os.path.join(K, "strat_sessions.csv"))
        M["yday_mid"] = (M.yday_high + M.yday_low) / 2
        _DATA["M"] = M
    return _DATA


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
    v = M.get(name, np.nan)
    return np.full(390, float(v) if pd.notna(v) else np.nan)


def validate(spec):
    if not isinstance(spec, dict): raise Bad("spec must be an object")
    e = spec.get("entry") or {}
    if e.get("type") not in ("level", "time"): raise Bad("entry.type must be level or time")
    if e["type"] == "level":
        if e.get("level") not in LEVELS: raise Bad(f"unknown level '{e.get('level')}' (use one of {', '.join(LEVELS)})")
        if e.get("action") not in ("fade", "break"): raise Bad("entry.action must be fade or break")
        w = e.get("window") or ["08:30", "11:00"]
        if not (0 <= mins(w[0]) < mins(w[1]) <= 385): raise Bad("window must be within 08:30-14:55")
    else:
        if not (0 <= mins(e.get("at", "")) <= 380): raise Bad("entry.at must be 08:30-14:50")
    st, tg = spec.get("stop") or {}, spec.get("target") or {}
    if not (("points" in st and 2 <= float(st["points"]) <= 200) or ("range" in st and 0.03 <= float(st["range"]) <= 1.5)):
        raise Bad("stop must be {points: 2-200} or {range: 0.03-1.5}")
    if not (("R" in tg and 0.3 <= float(tg["R"]) <= 15) or ("points" in tg and 2 <= float(tg["points"]) <= 600) or tg.get("level") in LEVELS):
        raise Bad("target must be {R: 0.3-15}, {points: 2-600} or {level: <LEVEL>}")
    ex = spec.get("exit", "14:55")
    if not (1 <= mins(ex) <= 385): raise Bad("exit must be 08:31-14:55")
    return True


def _filters(spec, X):
    """Per-session trade side/filter arrays from formulas over known columns (leak-guarded by the engine)."""
    import test_engine as T
    D = data(); M = D["M"]; n = len(M); dates = pd.to_datetime(M.date)
    allow = np.ones(n, bool); side = np.zeros(n)
    if spec.get("filter"):
        f = T.evaluate(spec["filter"], X); allow = (f.reindex(dates).values > 0)
    e = spec["entry"]
    if e["type"] == "time":
        sd = e.get("side", "long")
        if sd in ("long", "short"): side[:] = 1 if sd == "long" else -1
        else:
            s = T.evaluate(sd, X).reindex(dates).values; side = np.sign(np.nan_to_num(s))
    return allow, side


def simulate_session(D, i, spec, side=0, entry_override=None, cost_mult=1.0, stop_mult=1.0, tgt_mult=1.0, win_shift=0):
    """One session -> (pnl points, R, side) or None if no trade."""
    O, H, L, C = D["O"][i], D["H"][i], D["L"][i], D["C"][i]; M = D["M"].iloc[i]
    e = spec["entry"]; xe = min(mins(spec.get("exit", "14:55")), 389)
    st = spec["stop"]
    stop_pts = float(st["points"]) if "points" in st else float(st["range"]) * float(M.fc_frac) * O[0]
    if not np.isfinite(stop_pts): return None
    stop_pts = max(round(stop_pts * stop_mult / TICK) * TICK, 2.0)
    if entry_override is not None:                                     # placebo: market entry at a random minute
        k, s = entry_override
        ep = O[k] + s * TICK
    elif e["type"] == "time":
        k = mins(e["at"]); s = side
        if s == 0: return None
        ep = O[k] + s * TICK
    else:
        w0 = max(mins(e.get("window", ["08:30"])[0]), 0); w1 = min(mins(e.get("window", ["08:30", "11:00"])[1]) + win_shift, xe - 1)
        lv = level_path(D, i, e["level"])
        if e["level"] in ("or15_high", "or15_low"): w0 = max(w0, 15)
        if w1 <= w0 or not np.isfinite(lv[w0]): return None
        ref = O[w0] if w0 == 0 else C[w0 - 1]
        above = lv[w0] > ref
        if abs(lv[w0] - ref) < TICK: return None
        if e["action"] == "fade":
            s = -1 if above else 1
            hit = (H[w0:w1 + 1] >= lv[w0:w1 + 1] + TICK) if above else (L[w0:w1 + 1] <= lv[w0:w1 + 1] - TICK)
        else:
            s = 1 if above else -1
            hit = (H[w0:w1 + 1] >= lv[w0:w1 + 1] + TICK) if above else (L[w0:w1 + 1] <= lv[w0:w1 + 1] - TICK)
        if not hit.any(): return None
        k = w0 + int(np.argmax(hit)); lvl = lv[k]
        conf = e.get("confluence")                                    # only trade if another level sits close by
        if conf:
            near = [abs(level_path(D, i, c)[k] - lvl) for c in conf.get("levels", []) if c != e["level"] and c in LEVELS]
            if not any(np.isfinite(x) and x <= float(conf.get("within", 10)) for x in near): return None
        ep = lvl if e["action"] == "fade" else lvl + s * 2 * TICK
    if k >= xe: return None
    stop = ep - s * stop_pts
    tg = spec["target"]
    if "R" in tg: tgt = ep + s * float(tg["R"]) * tgt_mult * stop_pts
    elif "points" in tg: tgt = ep + s * float(tg["points"]) * tgt_mult
    else:
        tl = level_path(D, i, tg["level"])[k]
        if not np.isfinite(tl) or (tl - ep) * s <= 2 * TICK: return None
        tgt = tl
    # fill bar: only the stop can hit (pessimistic)
    if (s == 1 and L[k] <= stop) or (s == -1 and H[k] >= stop):
        xp = stop - s * TICK
    else:
        j0, j1 = k + 1, xe
        if j0 >= j1:
            xp = O[xe] - s * TICK
        else:
            hs = (L[j0:j1] <= stop) if s == 1 else (H[j0:j1] >= stop)
            ht = (H[j0:j1] >= tgt + TICK) if s == 1 else (L[j0:j1] <= tgt - TICK)
            a = int(np.argmax(hs)) if hs.any() else 10 ** 6; b = int(np.argmax(ht)) if ht.any() else 10 ** 6
            if a == b == 10 ** 6: xp = O[xe] - s * TICK                   # time exit at the exit bar's open
            elif a <= b: xp = stop - s * TICK                             # stop first (or same bar)
            else: xp = tgt
    pnl = (xp - ep) * s - COMM * cost_mult
    return pnl, pnl / stop_pts, s, k


def backtest(spec, X, sessions=None, **kw):
    D = data(); M = D["M"]
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
    D = data(); rng = np.random.default_rng(seed); e = spec["entry"]
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
    ses = M.session.values; ses = ses[(ses >= T.session.min()) & (ses <= T.session.max())] if len(T) else ses
    pts = pd.Series(0.0, index=ses); pts[T.session.values] = T.pnl.values
    stop = float(np.median(np.abs(T.pnl[T.pnl < 0]))) if (T.pnl < 0).any() else 20.0
    return pts.values, np.where(pts.values != 0, -stop, 0.0), stop


def _sizer(spec, stop):
    """Sizing from the spec's optional "prop" block: {"risk": share of the buffer to the max loss risked per trade (default
    0.25), "eval_risk": override during the evaluation}. Contracts = floor(risk * buffer / (stop * $2 per MNQ point))."""
    import prop_sim
    pr = spec.get("prop") or {}; r = float(pr.get("risk", 0.25)); re_ = float(pr.get("eval_risk", r))
    r, re_ = min(max(r, 0.02), 0.9), min(max(re_, 0.02), 0.9)
    return lambda phase, profit, buf: int(((re_ if phase == "eval" else r) * buf) // (stop * prop_sim.MNQ))


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
    D = data(); rng = np.random.default_rng(11); e = spec["entry"]
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
    D = data(); M = D["M"]
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


def spec_id(spec):
    return hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]


SPEC_HELP = f"""{{"kind": "strategy", "name": "<short name>",
   "entry": {{"type": "level", "level": "<LEVEL>", "action": "fade|break", "window": ["08:30", "11:00"],
             "confluence": {{"levels": ["<LEVEL>", "..."], "within": 10}}}}   (confluence optional: trade only if one of
             those levels is within N points of the entry level at the touch)
         or {{"type": "time", "at": "09:00", "side": "long|short|<formula: > 0 long, < 0 short>"}},
   "filter": "<optional formula over known columns; trade only when > 0>",
   "stop": {{"points": 15}} or {{"range": 0.25}},   "target": {{"R": 3}} or {{"points": 40}} or {{"level": "<LEVEL>"}},
   "exit": "14:55", "prop": {{"risk": 0.25, "eval_risk": 0.4}}, "explain": "<one line>"}}
   (prop = optional sizing for prop accounts: share of the buffer to the max-loss floor risked per trade, funded / eval)
   (A COMPLETE intraday NQ strategy, backtested on 1-minute data 2014-2023 with pessimistic fills and costs, then a
   locked 2024-2026 exam. fade = limit order at the level against the approach; break = stop order through it.
   stop range = fraction of the options-implied day range. LEVELS: {LEVEL_HELP}.
   Filters may use Volta's power probabilities pw_takes_pdh, pw_takes_pdl, pw_gap_fill, pw_tail_day (0-1, known at the
   open), k_ columns, gex_rank, iv30, vix, vix_curve, nq_vs_es etc. Never y_ columns.)"""
