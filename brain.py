"""
brain.py - Volta's brain (v1): forecasts tomorrow's NQ range, recalls similar past
days from its memory bank, grades itself every evening and keeps learning.

Model: ridge regression on log NQ range, trained 2014-2025 on QQQ options + NQ data.
Walk-forward test 2017-2025 (2,226 unseen days): avg miss 0.532% vs 0.547% for the
plain options-priced move; 80% band held 80% of the time. Direction: no edge (not used).
"""
import json, os, urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "brain_model.json")
MEM = os.path.join(HERE, "brain_memory.csv")
PREDS = os.path.join(HERE, "brain_preds.csv")
UA = {"User-Agent": "Mozilla/5.0"}
LAST = {}                      # last forecast, for /odds


def L(x):
    return float(np.log(max(float(x), 1e-5)))


# ------------------------------------------------------------------ data
def yahoo(sym, rng="3mo"):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range={rng}"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    r = r["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    idx = [pd.Timestamp(datetime.fromtimestamp(t, timezone.utc).date()) for t in r["timestamp"]]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=idx, dtype=float)
    df = df[~df.index.duplicated(keep="last")].dropna()
    return df


def _atm_iv(d, lo, hi):
    a = d[(d.dte >= lo) & (d.dte <= hi) & d.delta.abs().between(.4, .6) & (d.iv > 0.03)]
    return float(a.iv.median()) if len(a) else float("nan")


def features(d, S, ts, gex_rank, quintile, implied_move, next_day, nq, qqq):
    """Same readings as the training memory (brain/build_memory.py), from today's chain."""
    m = json.load(open(MODEL))
    ts = pd.Timestamp(ts).normalize()
    nq = nq[nq.index <= ts]; qqq = qqq[qqq.index <= ts]
    if len(nq) < 21 or nq.index[-1] != ts:
        raise ValueError(f"NQ bars not up to date (last {nq.index[-1].date() if len(nq) else 'none'})")
    rng = (nq.high - nq.low) / nq.open
    c = qqq.close.copy()
    c.iloc[-1] = S if qqq.index[-1] == ts else c.iloc[-1]
    if qqq.index[-1] != ts:
        c.loc[ts] = S
    r = np.log(c).diff().dropna()
    iv30, iv7 = _atm_iv(d, 20, 45), _atm_iv(d, 3, 10)
    w = d[(d.dte >= 20) & (d.dte <= 45) & (d.iv > 0.03)]
    p25 = w[~w.is_call & w.delta.between(-.3, -.2)].iv.median()
    c25 = w[w.is_call & w.delta.between(.2, .3)].iv.median()
    g = d[(d.open_interest > 0) & (d.dte >= 0)]
    v = g[(g.iv > 0.03) & (g.iv < 3)]
    T = np.maximum(v.dte.values, 0.25) / 365
    iv = v.iv.values
    d1 = (np.log(S / v.strike.values) + 0.5 * iv * iv * T) / (iv * np.sqrt(T))
    d2 = d1 - iv * np.sqrt(T)
    pdf = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi)
    sg = np.where(v.is_call, 1.0, -1.0)
    vanna = float((sg * (-pdf * d2 / iv) * v.open_interest.values * 100 * S * 0.01).sum()
                  / (g.open_interest.sum() * 100) * 1e2) / S * 100       # scale-free (same as memory)
    ratio = m["ratio"].get(str(int(quintile)), 1.0) if quintile else 1.0
    nd = pd.Timestamp(next_day)
    f = {"l_bot": L(implied_move * ratio), "l_impl": L(implied_move),
         "l_rng": L(rng.iloc[-1]), "l_rng5": L(rng.tail(5).mean()), "l_rng20": L(rng.tail(20).mean()),
         "event_prem": implied_move / (iv30 / np.sqrt(252)), "term": iv7 / iv30, "l_iv30": L(iv30),
         "gex_rank": gex_rank, "next_dow": nd.dayofweek, "gap_days": (nd - ts).days,
         "skew": (p25 - c25) / iv30, "l_rv20": L(r.tail(20).std() * np.sqrt(252)),
         "r20": float(np.log(c.iloc[-1] / c.iloc[-21])), "vanna": vanna}
    bad = [k for k, x in f.items() if not np.isfinite(x)]
    if bad:
        raise ValueError("missing readings: " + ", ".join(bad))
    return f


# ------------------------------------------------------------------ thinking
def predict(f, close=None):
    """Range forecast; with today's NQ close also the likely / far (90%) high and low."""
    m = json.load(open(MODEL))
    x = np.array([f[k] for k in m["features"]])
    lp = m["intercept"] + float(np.dot(m["coef"], x))
    lo, hi = m["band80"]
    a, b = m["bot_map"]
    out = {"pred": float(np.exp(lp)), "lo": float(np.exp(lp + lo)), "hi": float(np.exp(lp + hi)),
           "bot": float(np.exp(a + b * f["l_bot"])), "version": m["version"]}
    if close and "hilo" in m:
        for side, sgn in (("up", 1), ("down", -1)):
            h = m["hilo"][side]
            base = h["a"] + h["b"] * lp
            key = "high" if side == "up" else "low"
            out[key + "_mid"] = close * (1 + sgn * float(np.exp(base + h["q50"])))
            out[key + "_far"] = close * (1 + sgn * float(np.exp(base + h["q90"])))
        out["close"] = close
    return out


def recall(f, k=None):
    m = json.load(open(MODEL))["knn"]
    mem = pd.read_csv(MEM, parse_dates=["date"]).dropna(subset=m["features"] + ["y_rng"])
    k = k or m["k"]
    mu, sd = np.array(m["mu"]), np.array(m["sd"])
    A = (mem[m["features"]].to_numpy(float) - mu) / sd
    q = (np.array([f[c] for c in m["features"]]) - mu) / sd
    dist = np.sqrt(((A - q) ** 2).sum(1))
    nn = mem.iloc[np.argsort(dist)[:k]]
    return {"n": len(mem), "k": k, "avg": float(nn.y_rng.mean()), "big": float((nn.y_rng > .025).mean()),
            "top": [(r.date.date(), float(r.y_rng), float(r.y_r) if r.y_r == r.y_r else None)
                    for r in nn.head(3).itertuples()]}


# ------------------------------------------------------------------ memory & self-grading
def grade(nq, qqq):
    """Fill in outcomes for past forecasts, add those days to the memory bank."""
    if not os.path.exists(PREDS):
        return []
    p = pd.read_csv(PREDS, parse_dates=["date", "next_date"])
    out = []
    rng = (nq.high - nq.low) / nq.open
    ret = np.log(qqq.close).diff()
    for c in ("actual_high", "actual_low", "high_mid", "high_far", "low_mid", "low_far"):
        if c not in p:
            p[c] = np.nan
    mem = pd.read_csv(MEM, parse_dates=["date"])
    for i, r in p[p.actual.isna()].iterrows():
        now = pd.Timestamp.now(tz="America/New_York")
        today = pd.Timestamp(now.date())
        if r.next_date not in rng.index or r.next_date > today or (r.next_date == today and now.hour < 16):
            continue                                    # outcome not known yet / bar still forming
        y = float(rng[r.next_date])
        p.loc[i, "actual"] = y
        p.loc[i, "actual_high"] = float(nq.high[r.next_date]); p.loc[i, "actual_low"] = float(nq.low[r.next_date])
        out.append(p.loc[i].to_dict())
        f = json.loads(r.feat)
        row = {"date": r.date, **f, "y_rng": y, "y_r": float(ret.get(r.next_date, np.nan))}
        mem = pd.concat([mem[mem.date != r.date], pd.DataFrame([row])], ignore_index=True)
    if out:
        p.to_csv(PREDS, index=False, date_format="%Y-%m-%d")
        mem.sort_values("date").to_csv(MEM, index=False, date_format="%Y-%m-%d", float_format="%.6f")
    return out


def log_pred(ts, next_day, f, pr):
    cols = ["date", "next_date", "pred", "lo", "hi", "bot", "version", "actual", "feat",
            "high_mid", "high_far", "low_mid", "low_far", "actual_high", "actual_low"]
    p = pd.read_csv(PREDS, parse_dates=["date", "next_date"]) if os.path.exists(PREDS) else pd.DataFrame(columns=cols)
    p = p[p.date != pd.Timestamp(ts)]
    row = {"date": pd.Timestamp(ts), "next_date": pd.Timestamp(next_day), "pred": round(pr["pred"], 6),
           "lo": round(pr["lo"], 6), "hi": round(pr["hi"], 6), "bot": round(pr["bot"], 6),
           "version": pr["version"], "actual": np.nan, "feat": json.dumps({k: round(v, 6) for k, v in f.items()}),
           **{k: round(pr[k], 2) for k in ("high_mid", "high_far", "low_mid", "low_far") if k in pr}}
    p = pd.concat([p, pd.DataFrame([row])], ignore_index=True)
    p.to_csv(PREDS, index=False, date_format="%Y-%m-%d")


def scorecard():
    m = json.load(open(MODEL))
    bt = m["backtest"]
    lines = [f"Backtest ({bt['n']} unseen days): brain miss {bt['miss_brain']:.2f}% vs options-only "
             f"{bt['miss_bot']:.2f}%, 80% band held {bt['band_hit']:.0%}"]
    if os.path.exists(PREDS):
        p = pd.read_csv(PREDS).dropna(subset=["actual"])
        if len(p):
            mb = (p.actual - p.pred).abs().mean() * 100
            mo = (p.actual - p.bot).abs().mean() * 100
            hit = ((p.actual >= p.lo) & (p.actual <= p.hi)).mean()
            wins = ((p.actual - p.pred).abs() < (p.actual - p.bot).abs()).mean()
            lines.append(f"LIVE ({len(p)} days): brain miss {mb:.2f}% vs options-only {mo:.2f}% | "
                         f"closer on {wins:.0%} of days | 80% band held {hit:.0%}"
                         + ("" if len(p) >= 60 else " - early, needs 60+ days"))
            hl = p.dropna(subset=["high_far", "low_far", "actual_high", "actual_low"]) if "high_far" in p else p.iloc[:0]
            if len(hl):
                inside = ((hl.actual_high <= hl.high_far) & (hl.actual_low >= hl.low_far)).mean()
                lines.append(f"LIVE high/low: whole day stayed inside my far levels on {inside:.0%} of "
                             f"{len(hl)} days (backtest ~80%)")
        else:
            lines.append("LIVE: no graded days yet")
    return lines


# ------------------------------------------------------------------ one evening
def evening(d, S, ts, gex_rank, quintile, implied_move, next_day, nq_level):
    """Returns (forecast_lines, journal_lines). Never raises."""
    journal, fc = [], []
    try:
        nqb, qb = yahoo("NQ%3DF"), yahoo("QQQ")
    except Exception as e:
        return [f"brain offline today (price data: {type(e).__name__})"], []
    try:
        for g in grade(nqb, qb):
            y, pr, lo, hi, bot = g["actual"], g["pred"], g["lo"], g["hi"], g["bot"]
            ok = lo <= y <= hi
            better = abs(y - pr) < abs(y - bot)
            journal.append(f"{g['next_date']:%a %d %b}: I said {pr*100:.2f}% (band {lo*100:.2f}-{hi*100:.2f}%), "
                           f"NQ moved {y*100:.2f}% high-to-low -> {'inside ✅' if ok else 'OUTSIDE ❌'}"
                           f"{', beat options-only' if better else ', options-only was closer'}")
            if g.get("high_far") == g.get("high_far"):
                hok, lok = g["actual_high"] <= g["high_far"], g["actual_low"] >= g["low_far"]
                journal.append(f"   high {g['actual_high']:,.0f} (my far level {g['high_far']:,.0f} {'✅' if hok else '❌'}), "
                               f"low {g['actual_low']:,.0f} (my far level {g['low_far']:,.0f} {'✅' if lok else '❌'})")
    except Exception as e:
        journal.append(f"(grading issue: {type(e).__name__}: {e})")
    try:
        f = features(d, S, ts, gex_rank, quintile, implied_move, next_day, nqb, qb)
        ts_ = pd.Timestamp(ts).normalize()
        close = float(nqb.close[ts_]) if ts_ in nqb.index else None
        pr = predict(f, close)
        LAST.clear(); LAST.update(pred=round(pr["pred"], 5), nq=round(close or nq_level, 2),
                                  day=f"{pd.Timestamp(next_day):%a %d %b}", date=str(pd.Timestamp(next_day).date()),
                                  gex_rank=round(float(gex_rank), 3), event_prem=round(float(f.get("event_prem", 1.0)), 3),
                                  **{k: round(pr[k], 2) for k in ("high_mid", "high_far", "low_mid", "low_far") if k in pr})
        rc = recall(f)
        log_pred(ts, next_day, f, pr)
        pts = lambda x: x * nq_level
        mood = ("calm" if pr["pred"] < 0.011 else "normal" if pr["pred"] < 0.018 else
                "lively" if pr["pred"] < 0.028 else "wild")
        fc = [f"🧠 BRAIN v{pr['version']} - tomorrow ({pd.Timestamp(next_day):%a %d %b}) looks {mood.upper()}",
              f"  NQ high-to-low range: ~{pr['pred']*100:.2f}% (~{pts(pr['pred']):,.0f} pts)",
              f"  80% band: {pr['lo']*100:.2f}% to {pr['hi']*100:.2f}% ({pts(pr['lo']):,.0f}-{pts(pr['hi']):,.0f} pts)",
              f"  options alone say ~{pr['bot']*100:.2f}%",
              ""]
        if "high_mid" in pr:
            fc += [f"HIGH / LOW (from today's NQ close {pr['close']:,.0f}):",
                   f"  likely high ~{pr['high_mid']:,.0f} | far high {pr['high_far']:,.0f} (90% of days stay below)",
                   f"  likely low  ~{pr['low_mid']:,.0f} | far low  {pr['low_far']:,.0f} (90% of days stay above)",
                   "  'likely' = coin flip it gets there. Whole day inside both far levels ~80% of the time.",
                   ""]
        fc += [
              f"MEMORY - today looks like 20 similar past days (of {rc['n']:,} I remember):",
              f"  their next day averaged a {rc['avg']*100:.2f}% range; {rc['big']:.0%} were big (>2.5%)"]
        for dt, y, r in rc["top"]:
            fc.append(f"  - {dt:%d %b %Y}: next day range {y*100:.2f}%" + (f", closed {r*100:+.2f}%" if r is not None else ""))
        fc.append("  (range only - I have no edge on direction, so I don't call it)")
    except Exception as e:
        fc = [f"🧠 brain: no forecast today ({type(e).__name__}: {str(e)[:120]})"]
    return fc, journal
