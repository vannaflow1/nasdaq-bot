"""
idea_lab.py - how the learning session tests an idea from a paper against Volta's memory
(brain_memory.csv: one row per market day 2014->today, readings + what happened next).

  import idea_lab as lab
  M = lab.memory()                                  # DataFrame indexed by date
  new = pd.DataFrame({"my_feature": ...}, index=M.index)   # built ONLY from columns known at that day's close
  print(lab.test_range(new))        # does it improve the brain's next-day NQ range forecast?
  print(lab.test_direction(signal)) # signal: +1 long / -1 short / 0 flat per day -> next-day QQQ direction

Walk-forward only (train on past years, test each later year). Verdicts are conservative:
PROMISING needs a clear out-of-sample gain in most years. Nothing here changes the live brain;
promising ideas are flagged for a human to review.
"""
import os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = ["l_bot", "l_rng", "l_rng5", "l_rng20", "event_prem", "term", "l_iv30", "gex_rank", "next_dow", "gap_days"]
COLUMNS_HELP = {
    "l_bot": "log options-priced next-day move x gamma ratio", "l_impl": "log options-priced next-day move (straddle)",
    "l_rng": "log today's NQ high-low range", "l_rng5": "log 5-day avg range", "l_rng20": "log 20-day avg range",
    "event_prem": "implied move / normal daily IV (>1 = something scheduled)", "term": "7d IV / 30d IV",
    "l_iv30": "log 30d ATM IV", "gex_rank": "dealer gamma rank vs last year (0-1)", "next_dow": "weekday of next session",
    "gap_days": "calendar days to next session", "skew": "25d put-call IV / ATM IV", "l_rv20": "log 20d realized vol",
    "r20": "20-day QQQ return", "vanna": "dealer vanna (scale-free)",
    "y_rng": "OUTCOME next-day NQ range (fraction)", "y_r": "OUTCOME next-day QQQ log return",
    "options pack": ("knowledge/options_pack.csv adds per day: ATM IV at 7/30/60/90 days, term slope, risk reversal, "
                     "butterfly, 10-delta wings, put/call OI and volume, turnover, OI concentration, near/far dealer gamma, "
                     "0DTE share, and a daily Heston fit (kappa, long-run vol, vol-of-vol, spot-vol correlation, current vol)"),
}


def memory():
    M = pd.read_csv(os.path.join(HERE, "brain_memory.csv"), parse_dates=["date"]).set_index("date").sort_index()
    return M[~M.index.duplicated(keep="last")]


def _ridge(X, y, a=0.11):
    mu, ym = X.mean(0), y.mean(); Xc = X - mu
    b = np.linalg.solve(Xc.T @ Xc + a * np.eye(X.shape[1]), Xc.T @ (y - ym))
    return ym - mu @ b, b


def test_range(extra, start=2017):
    M = memory(); D = M[BASE + ["y_rng"]].join(extra).replace([np.inf, -np.inf], np.nan).dropna()
    y = np.log(D.y_rng.clip(lower=1e-5)); cols = list(extra.columns)
    res = []
    for yr in sorted(set(D.index.year)):
        if yr < start: continue
        tr, te = D.index.year < yr, D.index.year == yr
        if tr.sum() < 500 or te.sum() < 50: continue
        out = {}
        for nm, cs in (("base", BASE), ("with_idea", BASE + cols)):
            i, b = _ridge(D.loc[tr, cs].values, y[tr].values)
            out[nm] = np.abs(np.exp(y[te].values) - np.exp(i + D.loc[te, cs].values @ b)).mean() * 100
        res.append(dict(year=yr, **out))
    R = pd.DataFrame(res)
    if R.empty:
        return "NOT TESTABLE (not enough overlapping days)"
    gain = (R.base.mean() - R.with_idea.mean()) / R.base.mean() * 100
    wins = int((R.with_idea < R.base).sum())
    verdict = ("PROMISING" if gain >= 1.0 and wins >= 0.7 * len(R) else "NOT CONFIRMED on my data")
    return (f"{verdict}: range-forecast miss {R.base.mean():.3f}% -> {R.with_idea.mean():.3f}% "
            f"({gain:+.1f}%), better in {wins}/{len(R)} unseen years")


def test_direction(signal, start=2017):
    """Judged against simply holding the same AVERAGE exposure all the time, so a mostly-long
    signal does not get credit for QQQ's normal upward drift."""
    M = memory(); D = pd.DataFrame({"s": signal}).join(M.y_r).dropna()
    D = D[D.index.year >= start]
    if (D.s != 0).sum() < 100:
        return "NOT TESTABLE (fewer than 100 signal days)"
    expo = D.s.mean()                                  # average exposure (e.g. long 60% of days -> 0.6)
    pnl = D.s * D.y_r
    active = pnl - expo * D.y_r                        # what the timing adds over constant exposure
    t = active.mean() / active.std() * np.sqrt(len(active))
    yrs = active.groupby(D.index.year).mean(); pos = int((yrs > 0).sum())
    on = D[D.s != 0]; hit = (np.sign(on.s) * on.y_r > 0).mean(); long_only = (on.y_r > 0).mean()
    verdict = "PROMISING" if t > 2.5 and pos >= 0.7 * len(yrs) else "NOT CONFIRMED on my data"
    return (f"{verdict}: {len(on)} signal days, hit {hit:.1%} (always-long {long_only:.1%}), "
            f"strategy {pnl.mean()*1e4:+.1f} bps/day vs {expo*D.y_r.mean()*1e4:+.1f} for the same average exposure held "
            f"constantly -> timing adds {active.mean()*1e4:+.1f} bps/day, t={t:.2f}, positive in {pos}/{len(yrs)} years")


def test_options(signal, gamma_rank=None):
    """Runs an idea as a REAL options trade on QQQ (knowledge/options_trades.csv, 2017-2025, built from the
    end-of-day option chains): signal > 0 -> SELL volatility that day (iron fly: sell the nearest-expiry ATM
    straddle at the bid, buy wings 2x the straddle away at the ask, held to expiry); signal < 0 -> BUY the
    straddle at the ask; otherwise no trade. All spreads paid. Judged against a placebo: the same signal
    shifted to random other dates 300 times (same number of trades, same mix), so luck and the general
    tendency of options to be over/underpriced can't fake an edge."""
    O = pd.read_csv(os.path.join(HERE, "knowledge", "options_trades.csv"), parse_dates=["date"]).set_index("date")
    s = pd.Series(signal).reindex(O.index)
    ok = s.notna()
    sv = np.sign(s[ok]).to_numpy(); O = O[ok]
    if (sv != 0).sum() < 100:
        return "NOT TESTABLE (fewer than 100 trade days)"
    def pnl_of(sig):
        return np.where(sig > 0, O.fly2_bp.to_numpy(), np.where(sig < 0, O.long_straddle_bp.to_numpy(), np.nan))
    p = pd.Series(pnl_of(sv), index=O.index).dropna()
    rng = np.random.default_rng(11); n = len(sv)
    plac = np.array([np.nanmean(pnl_of(np.roll(sv, int(rng.integers(60, n - 60))))) for _ in range(300)])
    pval = float((plac >= p.mean()).mean())
    h = len(p) // 2; m1, m2 = p.iloc[:h].mean(), p.iloc[h:].mean()
    yrs = p.groupby(p.index.year).mean(); pos = int((yrs > 0).sum())
    ns, nl = int((sv > 0).sum()), int((sv < 0).sum())
    risk = (p / O.fly2_maxloss_bp.reindex(p.index).where(pd.Series(sv, index=O.index).reindex(p.index) > 0)).mean()
    overlap = ""
    if gamma_rank is not None:
        g = pd.Series(gamma_rank).reindex(O.index)
        on = pd.Series(sv > 0, index=O.index)
        if on.sum():
            overlap = f"; {((g > 0.7) & on).sum() / on.sum():.0%} of its sell days are high-gamma days (the known edge)"
    verdict = ("PROMISING" if p.mean() > 0 and pval < 0.05 and m1 > 0 and m2 > 0 and pos >= 0.7 * len(yrs)
               else "NOT CONFIRMED on my data")
    return (f"{verdict}: {ns} sell-vol + {nl} buy-vol trades on real QQQ option prices, avg {p.mean():+.1f} bp of QQQ per trade "
            f"(placebo avg {plac.mean():+.1f}, p={pval:.3f}), halves {m1:+.1f}/{m2:+.1f}, win {(p > 0).mean():.0%}, "
            f"worst {p.min():.0f} bp, positive in {pos}/{len(yrs)} years"
            + (f", sell trades return {risk:+.1%} of max risk" if ns else "") + overlap)


POWERS = {"trend_day": "next session is a trend day (body >= 60% of the range)",
          "extreme_first_hour": "one of the day's extremes is set in the first hour",
          "first_hour_continues": "the rest of the day continues the first hour's direction",
          "takes_pdh": "takes yesterday's high (days opening inside yesterday's range)",
          "takes_pdl": "takes yesterday's low (days opening inside yesterday's range)",
          "gap_fill": "the opening gap fills (gaps >= 0.2%)", "tail_day": "range 1.8x+ its 20-day norm",
          "inside_day": "inside day", "outside_day": "outside day"}


def test_power(signal, power, start=2017):
    """Does a formula help predict one of Volta's yes/no questions about the next session? Walk-forward logistic
    regression of the question on the signal; judged against the plain base rate of the training years."""
    from math import exp
    T = pd.read_csv(os.path.join(HERE, "knowledge", "power_targets.csv"), parse_dates=["date"]).set_index("date")
    if power not in T: return f"NOT TESTABLE (unknown power '{power}')"
    D = pd.DataFrame({"s": signal}).join(T[power].rename("y")).replace([np.inf, -np.inf], np.nan).dropna()
    if len(D) < 600: return "NOT TESTABLE (too little overlapping data)"
    ps, ys, wins, yrs = [], [], 0, 0
    for yr in sorted(set(D.index.year)):
        if yr < start: continue
        tr, te = D[D.index.year < yr], D[D.index.year == yr]
        if len(tr) < 400 or len(te) < 40: continue
        mu, sd = tr.s.mean(), tr.s.std() or 1.0; x = ((tr.s - mu) / sd).clip(-5, 5).values; y = tr.y.values
        a, b = np.log(y.mean() / (1 - y.mean())), 0.0
        for _ in range(300):                                   # small ridge-logistic fit by gradient steps
            p = 1 / (1 + np.exp(-(a + b * x))); a -= 0.5 * (p - y).mean(); b -= 0.5 * (((p - y) * x).mean() + 0.01 * b)
        xt = ((te.s - mu) / sd).clip(-5, 5).values; p = 1 / (1 + np.exp(-(a + b * xt))); base = y.mean()
        yrs += 1; wins += ((te.y - base) ** 2).mean() > ((te.y - p) ** 2).mean()
        ps += list(p); ys += list(te.y)
    ps, ys = np.array(ps), np.array(ys)
    if not len(ys): return "NOT TESTABLE (no test years)"
    bss = (1 - ((ys - ps) ** 2).mean() / ((ys - ys.mean()) ** 2).mean()) * 100
    order = np.argsort(ps); lo, hi = ys[order[: len(ys) // 5]].mean(), ys[order[-len(ys) // 5:]].mean()
    verdict = "PROMISING" if bss > 1.0 and wins >= 0.7 * yrs else "NOT CONFIRMED on my data"
    return (f"{verdict}: power '{power}' (base {ys.mean():.0%}): lowest-fifth days {lo:.0%} vs highest-fifth {hi:.0%}, "
            f"Brier skill {bss:+.1f}%, better than the base rate in {wins}/{yrs} unseen years")

def _fact(T):
    T = T.dropna()
    if not len(T): return "no data"
    binary = set(np.unique(T.values)) <= {0.0, 1.0}
    fmt = (lambda v: f"{v:.0%}") if binary else (lambda v: f"{v:.3g}")
    a, b = T[T.index.year <= 2019], T[T.index.year >= 2020]
    head = f"happens on {fmt(T.mean())} of {len(T)} sessions" if binary else f"average {fmt(T.mean())}, median {fmt(T.median())} over {len(T)} sessions"
    return head + f" (2014-19: {fmt(a.mean()) if len(a) else '-'}, 2020-25: {fmt(b.mean()) if len(b) else '-'})"


def test_question(T, P=None, start=2017):
    """A question Volta asked itself. Always answers the plain fact; if a predictor is given, checks walk-forward whether it
    predicts the answer better than the base rate / average of the training years."""
    T = pd.Series(T, dtype=float).replace([np.inf, -np.inf], np.nan)
    fact = _fact(T)
    if P is None:
        return f"FACT: {fact}"
    D = pd.DataFrame({"s": pd.Series(P, dtype=float), "y": T}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(D) < 500 or D.s.nunique() < 2:
        return f"FACT: {fact}. Predictor: NOT TESTABLE (too little data)"
    binary = set(np.unique(D.y.values)) <= {0.0, 1.0}
    ps, ys, wins, yrs = [], [], 0, 0
    for yr in sorted(set(D.index.year)):
        if yr < start: continue
        tr, te = D[D.index.year < yr], D[D.index.year == yr]
        if len(tr) < 400 or len(te) < 40: continue
        mu, sd = tr.s.mean(), tr.s.std() or 1.0; x = ((tr.s - mu) / sd).clip(-5, 5).values; y = tr.y.values
        xt = ((te.s - mu) / sd).clip(-5, 5).values
        if binary:
            if y.mean() in (0, 1): continue
            a, b = np.log(y.mean() / (1 - y.mean())), 0.0
            for _ in range(300):
                p = 1 / (1 + np.exp(-(a + b * x))); a -= 0.5 * (p - y).mean(); b -= 0.5 * (((p - y) * x).mean() + 0.01 * b)
            pt = 1 / (1 + np.exp(-(a + b * xt)))
        else:
            b = np.cov(x, y)[0, 1] / (x.var() + 1e-9) * len(x) / (len(x) + 50); pt = y.mean() + b * xt   # shrunk OLS
        base = y.mean(); yrs += 1; wins += ((te.y - base) ** 2).mean() > ((te.y - pt) ** 2).mean()
        ps += list(pt); ys += list(te.y)
    if not yrs: return f"FACT: {fact}. Predictor: NOT TESTABLE (no test years)"
    ps, ys = np.array(ps), np.array(ys)
    skill = (1 - ((ys - ps) ** 2).mean() / ((ys - ys.mean()) ** 2).mean()) * 100
    order = np.argsort(ps); k = len(ys) // 5; lo, hi = ys[order[:k]].mean(), ys[order[-k:]].mean()
    fmt = (lambda v: f"{v:.0%}") if binary else (lambda v: f"{v:.3g}")
    ok = skill > (1.0 if binary else 0.5) and wins >= 0.7 * yrs
    return (f"{'PROMISING' if ok else 'NOT CONFIRMED on my data'}: FACT: {fact}. Predictor: lowest-fifth days {fmt(lo)} vs "
            f"highest-fifth {fmt(hi)}, skill {skill:+.1f}% vs the base rate, better in {wins}/{yrs} unseen years")

if __name__ == "__main__":
    M = memory()
    print(len(M), "days in memory;", M.index.min().date(), "->", M.index.max().date())
    # sanity demo: an idea that should NOT help (random noise)
    rng = np.random.default_rng(0)
    print("noise:", test_range(pd.DataFrame({"noise": rng.normal(size=len(M))}, index=M.index)))
    print("skew:", test_range(M[["skew"]]))
    print("momentum dir:", test_direction(np.sign(M.r20)))
    print("options, sell vol on high gamma:", test_options((M.gex_rank > 0.7).astype(float), M.gex_rank))
    print("options, noise:", test_options(pd.Series(rng.choice([-1.0, 0.0, 1.0], len(M)), index=M.index), M.gex_rank))
