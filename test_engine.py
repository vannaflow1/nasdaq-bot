"""
test_engine.py - Volta's free, always-on idea tester (GitHub Actions).
  1. A free AI translates each queued idea into a small formula over Volta's memory columns
     (or picks a ready-made model template such as GARCH).
  2. The formula is checked: only known columns and whitelisted functions, nothing that can
     look into the future. Anything invalid -> "TRANSLATION FAILED" (never a fake result).
  3. The fixed, verified backtest code in idea_lab.py runs it (walk-forward 2017-2025;
     direction ideas judged against holding the same average exposure; options ideas traded on real
     QQQ option prices with spreads, judged against a shifted-date placebo).
PROMISING results go to knowledge/review_queue.json for a weekly human-grade review.
"""
import ast, json, math, os, re, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
import idea_lab
TESTQ, LIB, IDEAS, ANN, REVIEW, STATS = (os.path.join(K, f) for f in
    ("test_queue.json", "library.jsonl", "ideas.csv", "announce.json", "review_queue.json", "engine_stats.json"))

# ------------------------------------------------------------------ data the formulas may use (all known at the close)
def frame():
    M = idea_lab.memory().copy()
    X = pd.DataFrame(index=M.index)
    for c in ["l_bot", "l_impl", "l_rng", "l_rng5", "l_rng20", "event_prem", "term", "l_iv30", "gex_rank",
              "next_dow", "gap_days", "skew", "l_rv20", "r20", "vanna"]:
        if c in M: X[c] = M[c]
    X["r1"] = M.y_r.shift(1)                          # today's QQQ return (yesterday's 'next-day' outcome)
    X["iv30"] = np.exp(M.l_iv30); X["rv20"] = np.exp(M.l_rv20); X["impl"] = np.exp(M.l_impl)
    X["rng"] = np.exp(M.l_rng); X["rng5"] = np.exp(M.l_rng5); X["rng20"] = np.exp(M.l_rng20)
    X["vrp"] = X.iv30 - X.rv20
    nd = pd.DatetimeIndex(X.index + pd.to_timedelta(X.gap_days.fillna(1).values, unit="D"))
    X["next_opex"] = ((nd.weekday == 4) & (nd.day >= 15) & (nd.day <= 21)).astype(float)   # monthly expiration next
    st = os.path.join(K, "session_table.csv")              # open-ended session facts: k_* known at the open, y_* what happened
    if os.path.exists(st):
        Q = pd.read_csv(st, parse_dates=["date"]).set_index("date").drop(columns=["session"], errors="ignore")
        Q = Q[~Q.index.duplicated()]
        for c in [c for c in Q if c.startswith("y_")]:
            Q["p_" + c[2:]] = Q[c].shift(1)                     # yesterday's outcome = known today
        X = X.join(Q, how="left")
    sp = os.path.join(K, "strat_sessions.csv")             # Volta's power probabilities (walk-forward, known at the open)
    if os.path.exists(sp):
        P = pd.read_csv(sp, usecols=lambda c: c == "date" or c.startswith("pw_"), parse_dates=["date"]).dropna(subset=["date"]).set_index("date")
        X = X.join(P[~P.index.duplicated()], how="left")
    for extra in ("macro_daily.csv", "spx_daily.csv"):     # market-wide context (VIX family, ES, rates, dollar) + SPX options
        f = os.path.join(K, extra)
        if os.path.exists(f):
            E = pd.read_csv(f, parse_dates=["date"]).set_index("date"); E = E[~E.index.duplicated()]
            X = X.join(E[[c for c in E if c not in X]], how="left")
    pack = os.path.join(K, "options_pack.csv")             # full options-surface + Heston pack (from the 15M-row history)
    if os.path.exists(pack):
        P = pd.read_csv(pack, parse_dates=["date"]).set_index("date")
        X = X.join(P, how="left")
    return M, X

COLS_HELP = {"r1": "today's QQQ return", "r20": "20-day QQQ return", "iv30": "30-day implied vol (0.20 = 20%)",
             "rv20": "20-day realized vol", "vrp": "iv30 - rv20 (volatility premium)", "impl": "options-priced next-day move",
             "rng": "today's NQ high-low range (fraction)", "rng5": "5-day avg range", "rng20": "20-day avg range",
             "term": "7d IV / 30d IV", "skew": "25-delta put-call IV / ATM IV", "gex_rank": "dealer gamma rank 0-1",
             "vanna": "dealer vanna", "event_prem": "implied move vs normal (>1 = event tomorrow)",
             "next_dow": "weekday of next session 0=Mon", "gap_days": "calendar days to next session",
             "next_opex": "1 if the next session is the monthly options expiration (3rd Friday)",
             # options pack (QQQ option chains, one row per day)
             "atm7": "7-day ATM implied vol", "atm30": "30-day ATM IV", "atm60": "60-day ATM IV", "atm90": "90-day ATM IV",
             "term_slope": "atm90 - atm7", "term_ratio": "atm7 / atm90 (>1 = inverted, stress)",
             "pc_atm_iv": "ATM put IV - call IV", "rr25": "25-delta put IV - call IV (risk reversal)",
             "bf25": "25-delta butterfly (smile curvature)", "put10_wing": "10-delta put IV - ATM (crash premium)",
             "call10_wing": "10-delta call IV - ATM", "skew_norm": "rr25 / ATM IV",
             "pc_oi": "put/call open interest", "pc_vol": "put/call volume", "vol_oi": "option volume / open interest (turnover)",
             "oi_conc5": "share of open interest in the 5 biggest strikes", "gex_near7": "dealer gamma from expiries <= 7 days",
             "gex_far": "dealer gamma from expiries > 30 days", "dte0_oi_share": "share of open interest expiring within 1 day",
             "h_kappa": "Heston mean-reversion speed", "h_lrvol": "Heston long-run vol (sqrt theta)",
             "h_xi": "Heston vol-of-vol", "h_rho": "Heston spot-vol correlation", "h_spotvol": "Heston current vol (sqrt v0)",
             "h_rmse": "Heston fit error (vol points)",
             # session table (NY session 08:30-15:00 CT). k_ = known at the open, p_ = yesterday's value of a y_ column
             "k_gap": "gap at the NY open vs yesterday's NY close (%)", "k_on_range": "overnight range (%)",
             "k_on_vs_normal": "overnight range / 20-day avg NY range", "k_on_pos": "open position in the overnight range (0=low,1=high)",
             "k_on_return": "overnight return to the open (%)", "k_asia_range": "Asia range (%)", "k_london_range": "London range (%)",
             "k_open_vs_asia": "open position vs Asia range (0=low,1=high)", "k_open_vs_london": "open vs London range",
             "k_london_took_asia_high": "1 if London took the Asia high", "k_london_took_asia_low": "1 if London took the Asia low",
             "k_open_vs_yday": "open position vs yesterday's NY range", "k_yday_range": "yesterday's NY range (%)",
             "k_range20": "20-day avg NY range (%)", "k_dow": "weekday 0=Mon",
             "y_range": "OUTCOME NY range (%)", "y_return": "OUTCOME open-to-close return (%)", "y_close_loc": "OUTCOME close position in the day's range 0-1",
             "y_body": "OUTCOME |close-open| / range", "y_up_from_open": "OUTCOME high minus open (%)", "y_down_from_open": "OUTCOME open minus low (%)",
             "y_high_minute": "OUTCOME minutes after the open when the high was set", "y_low_minute": "OUTCOME minutes after the open of the low",
             "y_first_hour_range": "OUTCOME first-hour range (%)", "y_first_hour_return": "OUTCOME first-hour return (%)",
             "y_first30_return": "OUTCOME first-30-min return (%)", "y_last_hour_return": "OUTCOME last-hour return (%)",
             "y_rest_after_first_hour": "OUTCOME return from end of first hour to close (%)",
             "y_took_asia_high": "OUTCOME 1 if NY traded above the Asia high", "y_took_asia_low": "OUTCOME 1 if NY traded below the Asia low",
             "y_took_london_high": "OUTCOME NY above London high", "y_took_london_low": "OUTCOME NY below London low",
             "y_took_overnight_high": "OUTCOME NY above overnight high", "y_took_overnight_low": "OUTCOME NY below overnight low",
             "y_took_yday_high": "OUTCOME NY above yesterday's high", "y_took_yday_low": "OUTCOME NY below yesterday's low",
             "y_closed_above_yday_high": "OUTCOME closed above yesterday's high", "y_closed_below_yday_low": "OUTCOME closed below yesterday's low",
             "pw_takes_pdh": "Volta power: probability NY takes yesterday's high (0-1, at the open, days opening inside yesterday's range)",
             "pw_takes_pdl": "Volta power: probability NY takes yesterday's low", "pw_gap_fill": "Volta power: probability the gap fills",
             "pw_tail_day": "Volta power: probability of a tail day (range 1.8x+ normal)",
             "vix": "VIX (30-day S&P implied vol)", "vix9d": "9-day VIX", "vix3m": "3-month VIX", "vvix": "vol of VIX", "vix1d": "1-day VIX (2023+)",
             "vix_term": "vix9d / vix (>1 = near-term fear)", "vix_curve": "vix / vix3m (>1 = inverted, stress)", "vix_chg": "VIX % change today",
             "vvix_vix": "vvix / vix", "es_ret": "ES futures return today (%)", "es_ret5": "ES 5-day return (%)",
             "nq_vs_es": "NQ minus ES return today (tech leading > 0)", "nq_vs_es5": "NQ minus ES 5-day return",
             "spx_ret": "S&P 500 return today (%)", "us10y": "US 10-year yield (%)", "us10y_chg_bp": "10-year yield change today (bp)",
             "dxy_ret": "dollar index return today (%)",
             "spx_gexn": "SPX dealer gamma, normalised (collected from Oct 2026)", "spx_0dte_share": "SPX open interest expiring within 1 day (Oct 2026+)",
             "spx_atm_iv": "SPX nearest-expiry ATM IV (Oct 2026+)", "spx_skew": "SPX 25-delta put-call IV / ATM (Oct 2026+)",
             "y_gap_filled": "OUTCOME 1 if the gap filled",
             # ES futures (same session clock as NQ) + NYSE TICK breadth (the owner's 2014-2026 history)
             "k_es_on_range": "ES overnight range (%)", "k_es_gap": "ES gap at the open (%)", "k_es_on_return": "ES overnight return (%)",
             "k_es_open_vs_yday": "ES open vs yesterday's ES range (0=low,1=high)", "k_nq_minus_es_on": "NQ minus ES overnight return (%)",
             "k_smt_high": "1 if only ONE of NQ/ES took its Asia high before the open (SMT divergence)",
             "k_smt_high_nq_only": "1 if NQ took its Asia high before the open but ES did not",
             "k_smt_low": "1 if only one of NQ/ES took its Asia low before the open", "k_smt_low_nq_only": "1 if NQ took its Asia low but ES did not",
             "k_tick_yday_mean": "yesterday's average NYSE TICK", "k_tick_yday_max": "yesterday's highest TICK", "k_tick_yday_min": "yesterday's lowest TICK",
             "k_tick_yday_ext_up": "yesterday's count of 5-min bars with TICK >= +1000", "k_tick_yday_ext_dn": "yesterday's count of bars with TICK <= -1000",
             "k_tick_mean5": "5-day average NYSE TICK",
             "y_es_range": "OUTCOME ES NY range (%)", "y_es_return": "OUTCOME ES open-to-close (%)", "y_es_took_yday_high": "OUTCOME ES above its yesterday high",
             "y_es_took_yday_low": "OUTCOME ES below its yesterday low", "y_nq_minus_es": "OUTCOME NQ minus ES session return (%)",
             "y_tick_mean": "OUTCOME average NYSE TICK in the session", "y_tick_max": "OUTCOME highest TICK", "y_tick_min": "OUTCOME lowest TICK",
             "y_tick_ext_up": "OUTCOME bars with TICK >= +1000", "y_tick_ext_dn": "OUTCOME bars with TICK <= -1000",
             "y_tick_first30_mean": "OUTCOME average TICK in the first 30 minutes",
             # SPX weekly options 2019-2025 (the owner's tick data): dealer positioning known before the open
             "k_spx_gex": "SPX dealer gamma from open interest, 0-7 day options ($bn per 1%, price-normalised)",
             "k_spx_gex_flow": "SPX dealer gamma from REAL customer buy/sell flow since 7 days out",
             "k_spx_gex_0dte": "SPX dealer gamma of options expiring today", "k_spx_0dte_oi_share": "share of SPX weekly OI expiring today",
             "k_spx_pcr_oi": "SPX put/call open interest", "k_spx_flip_dist": "distance (%) from SPX to its gamma flip level",
             "k_spx_call_wall_dist": "distance (%) to the biggest SPX call-gamma strike within 3% above",
             "k_spx_put_wall_dist": "distance (%) to the biggest SPX put-gamma strike within 3% below (negative)",
             "k_spx_iv_near": "SPX nearest-expiry ATM implied vol at yesterday's close",
             "k_spx_cust_netprem_yday": "customers' net option premium bought yesterday ($m)",
             "k_spx_0dte_net_calls_yday": "customers' net 0DTE calls bought yesterday", "k_spx_0dte_net_puts_yday": "net 0DTE puts bought yesterday",
             "k_spx_volume_yday": "SPX weekly option volume yesterday", "k_spx_pc_vol_yday": "SPX put/call volume yesterday",
             "y_spx_h1_0dte_tilt": "OUTCOME first-hour 0DTE net call-minus-put buying / volume", "y_spx_h1_tilt": "OUTCOME first-hour call-put tilt (all expiries)",
             "y_spx_h1_netprem": "OUTCOME first-hour customer net premium ($m)", "y_vix_chg_h1": "OUTCOME first-hour VIX change", "y_vvix_chg_h1": "OUTCOME first-hour VVIX change"}
FUNCS = {  # name: (callable, help) - every window looks only backwards (today included)
    "mean": (lambda x, n: x.rolling(int(n)).mean(), "mean(x, n) rolling average of the last n days"),
    "std": (lambda x, n: x.rolling(int(n)).std(), "std(x, n)"),
    "median": (lambda x, n: x.rolling(int(n)).median(), "median(x, n)"),
    "rmax": (lambda x, n: x.rolling(int(n)).max(), "rmax(x, n)"),
    "rmin": (lambda x, n: x.rolling(int(n)).min(), "rmin(x, n)"),
    "z": (lambda x, n: (x - x.rolling(int(n)).mean()) / x.rolling(int(n)).std(), "z(x, n) z-score vs last n days"),
    "rank": (lambda x, n: x.rolling(int(n)).rank(pct=True), "rank(x, n) percentile 0-1 vs last n days"),
    "lag": (lambda x, n: x.shift(int(n)), "lag(x, n) value n days ago (n >= 1)"),
    "ewm": (lambda x, n: x.ewm(span=int(n)).mean(), "ewm(x, n) exponential average"),
    "csum": (lambda x, n: x.rolling(int(n)).sum(), "csum(x, n) rolling sum"),
    "log": (lambda x: np.log(x.where(x > 0)), "log(x)"), "abs": (lambda x: x.abs(), "abs(x)"),
    "sign": (lambda x: np.sign(x), "sign(x)"), "sqrt": (lambda x: np.sqrt(x.where(x >= 0)), "sqrt(x)"),
    "clip": (lambda x, a, b: x.clip(a, b), "clip(x, lo, hi)"),
    "where": (lambda c, a, b: pd.Series(np.where(c, a, b), index=c.index) if hasattr(c, "index") else (a if c else b),
              "where(cond, a, b)"),
}


class Bad(Exception):
    pass


PRED_OK = lambda c: not c.startswith("y_")                 # predictors: anything known before the session
TARGET_OK = lambda c: True                                 # question targets may scale outcomes by known values...


def evaluate(expr, X, allow=PRED_OK):
    """Safe evaluation of a tiny formula language. Raises Bad with a reason."""
    if len(expr) > 400: raise Bad("formula too long")
    tree = ast.parse(expr, mode="eval")
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return float(n.value)
        if isinstance(n, ast.Name):
            if n.id not in X: raise Bad(f"unknown column '{n.id}'")
            if not allow(n.id): raise Bad(f"'{n.id}' can't be used on this side (it would peek at the answer)")
            return X[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd, ast.Not)):
            v = ev(n.operand); return -v if isinstance(n.op, ast.USub) else (~v.astype(bool) if isinstance(n.op, ast.Not) else v)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.BitAnd, ast.BitOr)):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
            if isinstance(n.op, ast.Mult): return a * b
            if isinstance(n.op, ast.Div): return a / b
            if isinstance(n.op, ast.Pow): return a ** b
            if isinstance(n.op, ast.BitAnd): return (a.astype(bool) & b.astype(bool)).astype(float)
            return (a.astype(bool) | b.astype(bool)).astype(float)
        if isinstance(n, ast.BoolOp):
            vals = [ev(v).astype(bool) for v in n.values]; out = vals[0]
            for v in vals[1:]: out = (out & v) if isinstance(n.op, ast.And) else (out | v)
            return out.astype(float)
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            a, b = ev(n.left), ev(n.comparators[0]); op = n.ops[0]
            r = {ast.Gt: a > b, ast.Lt: a < b, ast.GtE: a >= b, ast.LtE: a <= b}.get(type(op))
            if r is None: raise Bad("only > < >= <= comparisons allowed")
            if not hasattr(r, "astype"): return float(r)
            r = r.astype(float)
            for side in (a, b):                                   # missing data stays missing, never "no"
                if hasattr(side, "notna"): r = r.where(side.notna())
            return r
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
            args = [ev(a) for a in n.args]
            if n.func.id == "lag" and (len(args) < 2 or args[1] < 1): raise Bad("lag needs n >= 1 (no peeking ahead)")
            if n.func.id in ("mean", "std", "median", "rmax", "rmin", "z", "rank", "ewm", "csum") and not (2 <= args[1] <= 504):
                raise Bad("window must be 2-504 days")
            return FUNCS[n.func.id][0](*args)
        raise Bad(f"not allowed: {ast.dump(n)[:60]}")
    out = ev(tree)
    if not isinstance(out, pd.Series): raise Bad("formula must depend on the data")
    out = out.replace([np.inf, -np.inf], np.nan)
    if out.notna().sum() < 500 or out.nunique() < 2: raise Bad("formula gives too little usable data")
    return out


# ------------------------------------------------------------------ model templates
def garch_feature(X, kind="garch"):
    """Next-day volatility forecast made at each close, parameters fit on PAST years only (refit yearly)."""
    from arch import arch_model
    r = (X.r1 * 100).dropna(); out = pd.Series(np.nan, index=X.index)
    mk = lambda data: arch_model(data, vol="EGARCH" if kind == "egarch" else "GARCH", p=1, o=1 if kind in ("gjr", "egarch") else 0,
                                 q=1, dist="t", rescale=False)
    for yr in range(2017, 2026):
        tr = r[r.index.year < yr]; te = r[r.index.year == yr]
        if len(tr) < 500 or len(te) == 0: continue
        params = mk(tr).fit(disp="off").params
        fc = mk(r[r.index.year <= yr]).fix(params).forecast(horizon=1, start=te.index[0], reindex=False)
        v = fc.variance["h.1"]                                   # made at close t, for day t+1
        out.loc[v.index] = np.log(np.sqrt(v) / 100)
    return out


def run_spec_question_fact(spec, X):
    if not re.search(r"\by_\w+", spec.get("target") or ""): raise Bad("the answer must use at least one y_ outcome column")
    T = evaluate(spec.get("target") or "", X, allow=TARGET_OK)
    return idea_lab.test_question(T, None), f"Q: {(spec.get('question') or '').strip()} | answer = `{spec.get('target')}` | fact only"


def run_spec(spec, X):
    kind = spec.get("kind")
    if kind == "strategy":
        import strategy_lab
        try:
            return strategy_lab.evaluate(spec, X, source=spec.get("_source", "engine"))
        except strategy_lab.Bad as e:
            raise Bad(str(e))
    if kind == "unfit":
        return "DOESN'T FIT MY DATA - " + (spec.get("why") or "needs data Volta doesn't have"), ""
    if kind == "template":
        t = {"arch": "garch", "garch(1,1)": "garch", "gjr-garch": "gjr", "tgarch": "gjr", "volatility_timing": "voltiming",
             "vol_timing": "voltiming"}.get(str(spec.get("template")).lower(), str(spec.get("template")).lower())
        if t in ("garch", "gjr", "egarch"):
            f = garch_feature(X, t)
            yrs = sorted(set(f.dropna().index.year))
            return idea_lab.test_range(pd.DataFrame({"garch": f})), (f"{t.upper()}(1,1) volatility forecast (refit yearly on past "
                   f"data only, years {yrs[0] if yrs else '-'}-{yrs[-1] if yrs else '-'}) added to the brain's range model")
        if t == "voltiming":
            tgt = float((spec.get("params") or {}).get("target", 0.18))
            s = (tgt / X.rv20).clip(0, 2)
            return idea_lab.test_direction(s), f"long QQQ scaled by {tgt:.0%} / 20-day realized vol (0-2x)"
        raise Bad(f"unknown template '{t}'")
    expr = spec.get("expr") or ""
    if kind == "question" and not expr.strip():
        return run_spec_question_fact(spec, X)
    for t in ("garch", "gjr", "egarch"):                   # model forecasts usable as columns too
        if t in expr and t not in X:
            X[t] = garch_feature(X, t)
    v = evaluate(expr, X)
    if kind == "range":
        return idea_lab.test_range(pd.DataFrame({"idea": v})), f"feature `{expr}` added to the brain's range model"
    if kind == "direction":
        rule = spec.get("rule", "long_flat")
        s = {"long_flat": (v > 0).astype(float), "short_flat": -(v > 0).astype(float), "long_short": np.sign(v)}.get(rule)
        if s is None: raise Bad("rule must be long_flat, short_flat or long_short")
        s = s.where(v.notna())
        return idea_lab.test_direction(s), f"{rule.replace('_', '/')} on `{expr}` (positive = signal on)"
    if kind == "question":
        tgt = spec.get("target") or ""
        if not re.search(r"\by_\w+", tgt): raise Bad("the answer must use at least one y_ outcome column")   # ...but must be about the session
        T = evaluate(tgt, X, allow=TARGET_OK)
        P = evaluate(expr, X) if expr.strip() else None
        q = (spec.get("question") or "").strip()
        return idea_lab.test_question(T, P), f"Q: {q} | answer = `{tgt}`" + (f" | predicted by `{expr}`" if P is not None else " | fact only")
    if kind == "power":
        pw = spec.get("power", "")
        return (idea_lab.test_power(v, pw), f"`{expr}` as a predictor of '{pw}' ({idea_lab.POWERS.get(pw, '?')})")
    if kind == "options":
        s = np.sign(v).where(v.notna())
        return (idea_lab.test_options(s, X.get("gex_rank")),
                f"`{expr}`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade")
    raise Bad("kind must be direction, range, options, power, template or unfit")


# ------------------------------------------------------------------ translator (free AI)
def translator_prompt():
    import strategy_lab
    cols = "\n".join(f"  {k}: {v}" for k, v in COLS_HELP.items())
    fns = "\n".join(f"  {v[1]}" for v in FUNCS.values())
    return f"""You translate a trading idea into a test for Volta's backtest engine. Data: one row per trading day
(2014-2025), all values known at that day's close. The engine predicts the NEXT day.
Columns:
{cols}
Functions (all look only backwards):
{fns}
Operators: + - * / ** > < >= <= and or. No other code.

Reply ONLY with JSON in one of these shapes:
{{"kind": "direction", "expr": "<formula>", "rule": "long_flat|long_short|short_flat", "explain": "<one line>"}}
   expr > 0 means the signal is ON (long_flat: long when on, else flat; long_short: sign of expr).
{{"kind": "range", "expr": "<formula>", "explain": "<one line>"}}   (idea predicts how BIG tomorrow's move is)
{{"kind": "options", "expr": "<formula>", "explain": "<one line>"}}   (idea about SELLING or BUYING options/volatility:
   expr > 0 = sell volatility that day (short QQQ iron fly), expr < 0 = buy volatility (long straddle), 0 = no trade.
   Use where(cond, 1, 0) for "sell only when ..." and where(cond, -1, 0) for "buy only when ..." so other days are no trade.
   Tested on REAL QQQ option prices 2017-2025 with spreads paid. Use this for volatility risk premium, option selling,
   straddles, event vol, "options are overpriced when..." ideas.)
{{"kind": "power", "expr": "<formula>", "power": "<one of: trend_day, extreme_first_hour, first_hour_continues, takes_pdh,
   takes_pdl, gap_fill, tail_day, inside_day, outside_day>", "explain": "<one line>"}}   (idea predicts a yes/no question about
   the next session: trend vs chop day, whether yesterday's high/low gets taken, whether the gap fills, a tail day, inside/
   outside day, whether the first hour's direction continues. Use this for intraday-pattern, liquidity-sweep, opening-range,
   gap and day-type ideas.)
{{"kind": "question", "question": "<plain-English question>", "target": "<formula over y_ columns: what happened>",
   "expr": "<formula over known columns that might predict it, or empty for a pure fact>", "explain": "<one line>"}}
   (Use this to ASK ANY NEW QUESTION about the next NY session (08:30-15:00 Chicago) that the fixed kinds don't cover.
   target must use only y_ columns; expr may use any other column incl. k_ (known at the open) and p_ (yesterday's outcome).
   A comparison target like y_high_minute < y_low_minute is a yes/no question; a number like y_up_from_open is a size question.)
__STRATEGY_HELP__
{{"kind": "template", "template": "garch|gjr|egarch|voltiming", "params": {{"target": 0.18}}, "explain": "<one line>"}}
{{"kind": "unfit", "why": "<what data would be needed>"}}   (ONLY if the columns truly cannot express it)

IMPORTANT: the options-surface and Heston columns (atm7..atm90, term_slope, rr25, bf25, put10_wing, pc_oi, gex_near7,
dte0_oi_share, h_xi, h_rho, h_kappa, h_lrvol, h_spotvol ...) ARE available every day. Ideas about stochastic volatility,
vol-of-vol, skew, the volatility surface, options positioning or 0DTE options can almost always be tested with them.
Templates available: garch, gjr, egarch, voltiming (ARCH ideas -> garch). In formulas you may also use the columns
garch, gjr, egarch (that model's next-day volatility forecast, log scale).
REALIZED VOLATILITY IS AVAILABLE: rv20 (from daily returns) and rng, rng5, rng20 (daily high-low range = a realized-vol
measure from intraday highs/lows). HAR models = rng, rng5, rng20. Do NOT call an idea unfit because it "needs realized vol".
MODEL TYPES: if a paper uses random forests, neural nets, LSTM, boosting etc., translate the INPUTS/signal it relies on into
a range or direction formula - Volta adds features to its own model, it does not need the paper's model type.
Use "unfit" only for data Volta truly lacks: order books, trade-by-trade or intraday option flow, news/social sentiment,
other assets (oil, bonds, single stocks), fundamentals.

Examples:
- "Go long when options are expensive vs realized vol": {{"kind":"direction","expr":"rank(vrp, 252) - 0.5","rule":"long_flat","explain":"long when the vol premium is above its 1-year median"}}
- "High implied vol predicts bigger next-day ranges beyond what options imply": {{"kind":"range","expr":"z(iv30, 60)","explain":"IV vs its 60-day norm"}}
- "Time-series momentum": {{"kind":"direction","expr":"r20","rule":"long_short","explain":"sign of the 20-day return"}}
- "GARCH forecasts volatility": {{"kind":"template","template":"garch","explain":"GARCH(1,1) next-day vol"}}
- "Heston: the correlation between volatility and returns matters for option prices": {{"kind":"range","expr":"h_rho","explain":"does the market-implied spot-vol correlation predict tomorrow's range"}}
- "High vol-of-vol warns of turbulence": {{"kind":"range","expr":"z(h_xi, 252)","explain":"vol-of-vol vs its 1-year norm"}}
- "The volatility risk premium: selling index options earns a premium, especially when implied vol is high vs realized": {{"kind":"options","expr":"where(rank(vrp, 252) > 0.7, 1, 0)","explain":"sell vol only when the vol premium is in its top 30% of the last year, else no trade"}}
- "Options are underpriced before turbulent periods with high vol-of-vol": {{"kind":"options","expr":"where(rank(h_xi, 252) > 0.7, -1, 0)","explain":"buy straddles only when Heston vol-of-vol is in its top 30%, else no trade"}}
- "Low volatility regimes produce more trend days": {{"kind":"power","expr":"rank(iv30, 252)","power":"trend_day","explain":"does the IV regime predict trend days"}}
- "Is the high of the day usually set before the low?": {{"kind":"question","question":"Is the NY high set before the low?","target":"y_high_minute < y_low_minute","expr":"","explain":"base rate"}}
- "After a big overnight range, does NY take the overnight extremes?": {{"kind":"question","question":"Does a wide overnight range make NY take the overnight high?","target":"y_took_overnight_high","expr":"k_on_vs_normal","explain":"overnight range vs normal as predictor"}}
- "Opening-range breakouts work on high-volatility days": {{"kind":"strategy","name":"OR15 break on high tail risk","entry":{{"type":"level","level":"or15_high","action":"break","window":["08:45","10:30"]}},"filter":"pw_tail_day - 0.1","stop":{{"range":0.15}},"target":{{"R":2}},"exit":"14:55","explain":"breakout of the first 15 minutes when Volta expects a big day"}}
- "Order-book imbalance predicts returns": {{"kind":"unfit","why":"needs intraday order book data"}}""".replace("__STRATEGY_HELP__", strategy_lab.SPEC_HELP.replace("{{", "{").replace("}}", "}"))


def first_json(text):
    """Tolerant: plain JSON first; then code fences, doubled braces {{ }}, or a Python-style dict with single quotes."""
    def scan(t):
        i = t.find("{")
        if i < 0: raise Bad("translator gave no JSON")
        try:
            return json.JSONDecoder().raw_decode(t[i:])[0]
        except ValueError:
            depth = 0
            for j, ch in enumerate(t[i:], i):
                depth += ch == "{"; depth -= ch == "}"
                if depth == 0:
                    frag = t[i:j + 1]; break
            else:
                raise Bad("translator JSON not closed")
            try:
                v = ast.literal_eval(frag.replace("true", "True").replace("false", "False").replace("null", "None"))
            except Exception as e:
                raise Bad(f"translator JSON unreadable ({type(e).__name__})")
            if not isinstance(v, dict): raise Bad("translator JSON is not an object")
            return v
    t = text.replace("```json", "").replace("```", "")
    try:
        return scan(t)
    except Bad:
        return scan(t.replace("{{", "{").replace("}}", "}"))


def translate(ask, idea, title):
    out, units = ask(translator_prompt(), f"Paper: {title}\nIdea: {idea}")
    return first_json(out), units


# ------------------------------------------------------------------ bookkeeping
def week():
    d = datetime.now(timezone.utc).isocalendar(); return f"{d[0]}-W{d[1]:02d}"


def record(item, verdict, how, spec):
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [json.loads(l) for l in open(LIB) if l.strip()] if os.path.exists(LIB) else []
    for x in lines:
        if x["id"] == item["id"]:
            x.setdefault("idea", {}).update(tested=True, verdict=verdict, detail=how, spec=spec, tested_by="engine")
    open(LIB, "w").write("\n".join(json.dumps(x) for x in lines) + "\n")
    if not os.path.exists(IDEAS): open(IDEAS, "w").write("date,paper_id,idea,verdict\n")
    with open(IDEAS, "a") as f:
        f.write(f'{today},{item["id"]},"{item["idea"][:200].replace(chr(34), chr(39))}","{verdict[:200].replace(chr(34), chr(39))}"\n')
    if spec.get("kind") == "question":
        with open(os.path.join(K, "questions.jsonl"), "a") as f:
            f.write(json.dumps({"date": today, "question": spec.get("question") or item["idea"][:200], "target": spec.get("target"),
                                "expr": spec.get("expr"), "verdict": verdict, "source": item.get("source", "paper"),
                                "inspired_by": item.get("title", "")[:150]}) + "\n")
    ann = json.load(open(ANN)) if os.path.exists(ANN) else []
    own = item.get("source") == "curiosity"
    ann.append({"title": (f"🛠️ Volta built a strategy: {str(spec.get('name') or item['idea'])[:90]}" if spec.get("kind") == "strategy" else
                          f"❓ Volta asked itself: {(spec.get('question') or item['idea'])[:90]}" if own else f"🧪 Idea tested: {item['idea'][:90]}"),
                "body": f"Paper: {item['title'][:150]}\nIdea: {item['idea'][:300]}\n\nResult: **{verdict}**\nHow: {how}"
                        + ("\n\nFlagged for a deeper review before anyone should trust it." if verdict.startswith("PROMISING") else "")})
    json.dump(ann, open(ANN, "w"), indent=1)
    if verdict.startswith("PROMISING"):
        rq = json.load(open(REVIEW)) if os.path.exists(REVIEW) else []
        rq.append({**item, "verdict": verdict, "how": how, "spec": spec, "date": today}); json.dump(rq, open(REVIEW, "w"), indent=1)
    st = json.load(open(STATS)) if os.path.exists(STATS) else {}
    w = st.setdefault(week(), {"tested": 0, "promising": 0, "not_confirmed": 0, "unfit": 0, "failed": 0})
    key = ("failed" if verdict.startswith("TRANSLATION FAILED") else "unfit" if verdict.startswith("DOESN'T FIT") else
           "promising" if verdict.startswith("PROMISING") else "not_confirmed")
    w[key] += 1; w["tested"] += 1
    json.dump(st, open(STATS, "w"), indent=1)


DISC = os.path.join(K, "discovered_powers.json")


def promote_power(spec, verdict):
    """A self-asked question that survived the stress test becomes a live line in the morning open read."""
    d = json.load(open(DISC)) if os.path.exists(DISC) else []
    if any(x["target"] == spec.get("target") and x["expr"] == spec.get("expr") for x in d): return
    d.append({"id": len(d) + 1, "date": datetime.now(timezone.utc).date().isoformat(), "question": spec.get("question", "")[:200],
              "target": spec.get("target"), "expr": spec.get("expr"), "verdict": verdict[:400], "active": True})
    json.dump(d, open(DISC, "w"), indent=1)
    ann = json.load(open(ANN)) if os.path.exists(ANN) else []
    ann.append({"title": f"⚡ Volta gave itself a new power: {spec.get('question', '')[:90]}",
                "body": f"{verdict[:600]}\n\nFrom now on this shows up in the morning open read in #live and /powers."})
    json.dump(ann, open(ANN, "w"), indent=1)


POOL = os.path.join(K, "feature_pool.json")
QSTATE = os.path.join(K, "questions_state.json")


def curiosity(ask, per_day=6):
    """Volta asks itself a new question, inspired by what it read recently, and queues it for testing."""
    today = datetime.now(timezone.utc).date().isoformat()
    st = json.load(open(QSTATE)) if os.path.exists(QSTATE) else {}
    if st.get("date") != today: st = {"date": today, "n": 0}
    if st["n"] >= per_day: return 0.0
    lib = [json.loads(l) for l in open(LIB) if l.strip()] if os.path.exists(LIB) else []
    recent = sorted(lib, key=lambda x: x.get("date", ""))[-10:]
    import random
    seeds = random.sample(recent, min(4, len(recent)))
    past = [json.loads(l)["question"] for l in open(os.path.join(K, "questions.jsonl"))] if os.path.exists(os.path.join(K, "questions.jsonl")) else []
    cols = "\n".join(f"  {k}: {v}" for k, v in COLS_HELP.items() if k[:2] in ("k_", "y_") or k in ("iv30", "rv20", "gex_rank", "impl", "rng20", "vrp", "skew", "term", "event_prem", "next_opex"))
    system = f"""You are Volta's curiosity. You study the Nasdaq futures (NQ) regular session 08:30-15:00 Chicago time and have
12 years of session data. Ask ONE new, concrete question a day trader would care about, inspired by the research below,
that you can answer with these columns (k_ = known at the open, p_<name> = yesterday's y_<name>, y_ = what happened):
{cols}
Functions: mean, std, rank, z, lag, abs, log, sign, clip, where; operators + - * / > < >= <= and or.
Rules: the ANSWER (target) uses y_ columns (it may divide by known values); the PREDICTOR (expr) uses only known columns
(k_, p_, iv30, gex_rank... NEVER y_) or is empty for a pure fact. Example: "do high-gamma days have smaller NY ranges?" ->
target "y_range / k_range20", expr "gex_rank". Do not repeat a question already asked. Reply ONLY with JSON:
{{"kind":"question","question":"...","target":"...","expr":"...","explain":"which research idea inspired it"}}"""
    user = ("Recent research:\n" + "\n".join(f"- {x['title'][:120]}: {(x.get('learned') or '')[:260]}" for x in seeds)
            + "\n\nQuestions already asked:\n" + "\n".join(f"- {q[:140]}" for q in past[-40:]))
    want_strategy = st["n"] % 2 == 1
    if want_strategy:
        import strategy_lab
        tried = [json.loads(l).get("name", "") for l in open(strategy_lab.LOG)] if os.path.exists(strategy_lab.LOG) else []
        system = (f"""You are Volta's strategy designer for Nasdaq futures (NQ), NY session 08:30-15:00 Chicago. Design ONE complete,
testable intraday strategy inspired by the research below and by what Volta already knows:
- PROVEN: dealer gamma sets the SIZE of the day (low gamma = big days); options overprice calm high-gamma days.
- Volta's powers (use as filters): pw_takes_pdh / pw_takes_pdl (chance NY takes yesterday's high/low), pw_gap_fill, pw_tail_day.
- Already FAILED mechanically: fading yesterday's high/low, Asia/London highs/lows, VWAP bands and the midnight open with a
  15-point stop and 4R target (stops run ~70% of the time; price overshoots levels by ~11 pts), also with level confluence.
Strategy format:
""" + strategy_lab.SPEC_HELP.replace("{{", "{").replace("}}", "}") + """
Known columns for filters/side formulas:
""" + cols + """
Do not repeat a strategy already tried. Reply ONLY with the JSON (kind "strategy").""")
        user = ("Recent research:\n" + "\n".join(f"- {x['title'][:120]}: {(x.get('learned') or '')[:260]}" for x in seeds)
                + "\n\nStrategies already tried:\n" + "\n".join(f"- {t[:120]}" for t in tried[-40:]))
    out, units = ask(system, user)
    try:
        spec = first_json(out)
        if want_strategy:
            if spec.get("kind") != "strategy": raise Bad("not a strategy")
            spec["_source"] = "curiosity"; spec.setdefault("question", "Strategy: " + str(spec.get("name", "")))
        elif spec.get("kind") != "question" or not spec.get("target"): raise Bad("not a question")
    except Exception as e:
        print("curiosity: unusable", e); return units
    tq = json.load(open(TESTQ)) if os.path.exists(TESTQ) else []
    tq.append({"id": f"q:{today}:{st['n']}", "title": ("Volta's own strategy" if want_strategy else "Volta's own question")
               + " (inspired by: " + "; ".join(x["title"][:60] for x in seeds[:2]) + ")",
               "idea": spec.get("question", "") if not want_strategy else "Strategy: " + str(spec.get("name", "")) + " - " + str(spec.get("explain", "")),
               "relevance": 6, "spec": spec, "source": "curiosity"})
    json.dump(tq, open(TESTQ, "w"), indent=1)
    st["n"] += 1; json.dump(st, open(QSTATE, "w"))
    print("curiosity asked:", spec.get("question"))
    return units


def add_to_pool(item, spec, verdict):
    """Near misses: range ideas that helped a little and fairly consistently, kept to be re-tested TOGETHER monthly."""
    import re
    m = re.search(r"\(([+-][\d.]+)%\), better in (\d+)/(\d+)", verdict)
    if not m or spec.get("kind") not in ("range", "template") or verdict.startswith("PROMISING"): return
    gain, w, n = float(m[1]), int(m[2]), int(m[3])
    if gain <= 0 or w < 0.55 * n: return
    pool = json.load(open(POOL)) if os.path.exists(POOL) else []
    key = spec.get("expr") or spec.get("template")
    if any((p.get("expr") or p.get("template")) == key for p in pool): return
    pool.append({"expr": spec.get("expr"), "template": spec.get("template") if spec.get("kind") == "template" else None,
                 "gain": gain, "years": f"{w}/{n}", "paper": item.get("title", "")[:120], "id": item.get("id"),
                 "added": datetime.now(timezone.utc).date().isoformat()})
    json.dump(pool, open(POOL, "w"), indent=1)


SKILL = {"range": r"\(([+-][\d.]+)%\)", "direction": r"timing adds ([+-][\d.]+)", "power": r"Brier skill ([+-][\d.]+)%",
         "question": r"skill ([+-][\d.]+)% vs the base rate"}


def _skill(kind, verdict):
    if kind == "options":
        a = re.search(r"avg ([+-][\d.]+) bp of QQQ per trade", verdict); b = re.search(r"placebo avg ([+-][\d.]+)", verdict)
        return float(a[1]) - float(b[1]) if a and b else None
    m = re.search(SKILL.get(kind, "$^"), verdict)
    return float(m[1]) if m else None


def stress(spec, X, verdict):
    """Free, immediate stress test of a PROMISING result: (1) nudge every number in the formula by -20%/+20%: a real
    effect should survive; (2) feed the same formula 1-12 months stale (lagged): a real day-ahead effect should be
    clearly better than its stale copies. Returns (label, detail)."""
    kind = spec.get("kind"); expr = spec.get("expr") or ""
    real = _skill(kind, verdict)
    if real is None or real <= 0 or kind == "template" or not expr.strip():
        return "NOT STRESS-TESTABLE", "no formula to nudge (template or pure fact)"
    def score(e):
        try:
            v, _ = run_spec({**spec, "expr": e}, X)
            return _skill(kind, v)
        except Exception:
            return None
    nums = [m for m in re.finditer(r"(?<![\w.])(\d+\.?\d*)(?![\w.])", expr)][:3]
    nudged = []
    for m in nums:
        val = float(m[1])
        for f in (0.8, 1.2):
            nv = val * f
            nv = str(max(2, round(nv))) if "." not in m[1] and val >= 2 else f"{nv:.4g}"
            nudged.append(score(expr[:m.start()] + nv + expr[m.end():]))
    ok = [x for x in nudged if x is not None]
    nudge_pass = (sum(x > 0.5 * real for x in ok) / len(ok)) if ok else None
    lags = [score(f"lag({expr}, {k})") for k in (21, 63, 126, 252)]
    lagok = [x for x in lags if x is not None]
    beaten = sum(x < 0.5 * real for x in lagok)
    detail = (f"skill {real:+.2f}; nudged formulas kept >= half the skill in "
              + (f"{sum(x > 0.5 * real for x in ok)}/{len(ok)}" if ok else "n/a (no numbers)")
              + f"; stale copies (lag 1-12 months) clearly worse in {beaten}/{len(lagok)}")
    if nudge_pass is not None and nudge_pass < 0.75:
        return "FRAGILE", detail
    if lagok and beaten < 3:
        return "SLOW REGIME EFFECT", detail                      # a stale signal works too: not a day-ahead edge
    return "SURVIVED", detail


def run(ask, max_items=3):
    tq = json.load(open(TESTQ)) if os.path.exists(TESTQ) else []
    if not tq: print("test queue empty"); return 0
    M, X = frame(); used = 0.0; n = 0
    tq.sort(key=lambda t: -t.get("relevance", 0))
    while tq and n < max_items:
        item = tq.pop(0); spec = {}
        try:
            try:
                if item.get("spec"):                                     # Volta's own question: already a spec
                    spec, u = item["spec"], 0.0
                else:
                    spec, u = translate(ask, item["idea"], item["title"])
                used += u
            except (Bad, ValueError) as e:
                if item.get("attempts", 0) < 1:              # one retry on the next run
                    item["attempts"] = item.get("attempts", 0) + 1; tq.append(item)
                    json.dump(tq, open(TESTQ, "w"), indent=1); print("translation retry later:", e); n += 1; continue
                raise Bad(f"translator output unusable ({e})")
            try:
                verdict, how = run_spec(spec, X)
            except Bad as e:                                       # one repair round: show the AI its exact mistake
                fix, u = ask(translator_prompt(), f"Paper: {item['title']}\nIdea: {item['idea']}\nYour previous JSON: {json.dumps(spec)}\n"
                             f"It was rejected: {e}. Remember: y_ columns are OUTCOMES and may only appear in a question's target; "
                             "predictor formulas (expr) use only columns known before the session. Reply with corrected JSON only.")
                used += u; spec = first_json(fix)
                verdict, how = run_spec(spec, X)
            if verdict.startswith("PROMISING") and spec.get("kind") != "strategy":   # the lab runs its own stress test
                label, sdetail = stress(spec, X, verdict)
                if label in ("SURVIVED", "NOT STRESS-TESTABLE"):
                    verdict = f"PROMISING (stress test: {label.lower()}) " + verdict[len("PROMISING"):]
                    how += f" | stress: {sdetail}"
                    if label == "SURVIVED" and spec.get("kind") == "question" and (spec.get("expr") or "").strip():
                        promote_power(spec, verdict)            # Volta gives itself a new live ability
                else:
                    verdict = f"NOT CONFIRMED after the stress test ({label.lower()}: {sdetail}) | first result: " + verdict
            add_to_pool(item, spec, verdict)
        except Bad as e:
            verdict, how = f"TRANSLATION FAILED - {e}", ""
        except Exception as e:
            verdict, how = f"TRANSLATION FAILED - {type(e).__name__}: {str(e)[:80]}", ""
        record(item, verdict, how, spec); n += 1
        json.dump(tq, open(TESTQ, "w"), indent=1)
        print(f"tested: {item['idea'][:60]} -> {verdict[:90]}")
    return used


if __name__ == "__main__":
    # offline self-test with hand-written specs (no AI)
    M, X = frame()
    for spec in [{"kind": "direction", "expr": "rank(vrp, 252) - 0.5", "rule": "long_flat"},
                 {"kind": "direction", "expr": "vrp", "rule": "long_short"},
                 {"kind": "range", "expr": "z(iv30, 60)"},
                 {"kind": "template", "template": "voltiming", "params": {"target": 0.18}},
                 {"kind": "direction", "expr": "lag(r1, -1)", "rule": "long_flat"},
                 {"kind": "direction", "expr": "__import__('os')", "rule": "long_flat"},
                 {"kind": "options", "expr": "where(gex_rank > 0.7, 1, 0)"},
                 {"kind": "options", "expr": "where(rank(vrp, 252) > 0.7, 1, 0)"},
                 {"kind": "range", "expr": "y_rng"}]:
        try:
            print(spec.get("expr") or spec.get("template"), "->", run_spec(spec, X)[0][:140])
        except Bad as e:
            print(spec.get("expr"), "-> REJECTED:", e)
