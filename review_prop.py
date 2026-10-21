"""review_prop.py - the IMMEDIATE review of a strategy that just passed the locked prop exam (no waiting for Sunday).

The owner's goal: a prop algo that passes evaluations and keeps paying out NOW and in the coming weeks. So the RECENT
regime decides; old years only guard against a strategy that is a lucky fit. Checks (v2, 21 Oct 2026):
  1. RECENT REGIME DECIDES: re-scored under the CURRENT simulator rules, payouts minus fee per eval must be > 0 on the
     locked 2024-26 exam years AND on 2022-23 (the two most recent independent stretches) AND for accounts started in the
     LATEST ~6 months of data (closest to the future - so an edge that already faded inside the exam period fails).
  2. LUCK ON THE UNSEEN YEARS: the same plan, sizing, stop and target with entries at a random minute (same side) or a
     coin-flip side on the 2024-26 days. If random entries pay about as much (p >= 0.10), the payouts come from the prop
     rules and the period, not from the strategy -> FLUKE.
  3. LUCKY-NUMBER TEST: the strategy stays FIXED - this only asks whether its exact numbers were a lucky pick out of the
     thousands of grid points Volta tried. Neighbouring settings (stop/target +-20%, entry +-15 min) on the RECENT years
     (2022-26) must mostly pay too (>= 4 of 6). If only the exact chosen numbers work, the result is almost surely
     selection luck and will not repeat.
  4. COSTS: 1.5x commissions and slippage on the exam years must still pay out more than the fee.
  5. NO ANTI-EDGE IN THE PAST (guard, not a requirement to have worked): over 2014-21 the strategy may have been dormant,
     but must not have lost clearly MORE than random entries with the same plan/sizing (the no-edge baseline). A
     strategy that was consistently worse than random for 8 years and good for 2 is far more likely luck than a new regime.
All pass -> CONFIRMED. A confirmed strategy is then watched on every new day (regime_watch below) and demoted
automatically if the coming weeks clearly break from what the review expected. Claude's nightly session double-checks
every automatic review once."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


# ------------------------------------------------------------------ review store (separate from the append-only strategy log)
# Long-running search jobs append to strategies.jsonl and their state commits win merge conflicts, so an edited line could be
# silently reverted (it happened on 21 Oct). Reviews therefore live in knowledge/reviews.json, keyed by the spec id; only
# reviewers write it. A review written into a strategies.jsonl line at append time is the fallback.
REVIEWS = os.path.join(HERE, "knowledge", "reviews.json")


def review_key(e):
    import strategy_lab as S
    return S.spec_id(e["spec"]) if isinstance(e.get("spec"), dict) else str(e.get("name"))


def load_reviews():
    import json
    try: return json.load(open(REVIEWS))
    except Exception: return {}


def save_review(e, **fields):
    import json
    R = load_reviews(); k = review_key(e); cur = R.get(k, {"name": e.get("name")})
    cur.update({k2: v for k2, v in fields.items() if v is not None}); cur["updated"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M")
    R[k] = cur; json.dump(R, open(REVIEWS, "w"), indent=1, default=float)


def effective(e, R=None):
    """The strategy entry with its latest review merged in (reviews.json wins over the line's own fields)."""
    R = load_reviews() if R is None else R; x = dict(e); x.update(R.get(review_key(e), {}))
    return x


def _ev(S, T, M, spec, plan):
    return S.prop_score(T, M, spec, plan)[0]["ev_per_eval"] if len(T) >= 30 else None


def _placebo(S, D, M, spec, plan, T, reps, seed):
    """EVs of random-entry versions of trades T (even reps: random minute, same side; odd: same minute, coin-flip side)."""
    rng = np.random.default_rng(seed); e = spec["entry"]
    lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
    hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2); evs = []
    for r in range(reps):
        rows = []
        import families as _F; intraday = _F.intraday_side(spec)
        for s_, i, sd, k0 in zip(T.session.values, T.i.values, T.side.values, T.k.values):
            even = r % 2 == 0 and not intraday                         # intraday-decided side: coin-flip twins only (no future info)
            side = int(sd) if even else int(rng.choice([-1, 1]))
            k = int(rng.integers(lo, hi)) if even else int(k0)
            x = S.simulate_session(D, int(i), spec, entry_override=(k, side))
            if x: rows.append((s_, i, x[0], x[1], x[2], x[3]))
        P = pd.DataFrame(rows, columns=["session", "i", "pnl", "R", "side", "k"])
        evs.append(_ev(S, P, M, spec, plan) if len(P) >= 30 else -999)
    return np.array(evs, float)


def review(spec, X, plan, exam_ev=None, reps=40, seed=3):
    import strategy_lab as S
    D = S.data(spec.get("market")); M = D["M"]
    allidx = np.arange(len(M)); T = S.backtest(spec, X, allidx); Ty = T.session.str[:4].astype(int)
    exam = np.where(M.session >= S.EXAM_FROM)[0]; recent = np.where(M.session >= "2022-01-01")[0]
    det, fails = {}, []
    # 1. recent regime decides (current simulator rules)
    E = T[Ty >= 2024]; V = T[(Ty >= 2022) & (Ty <= 2023)]
    ev_exam, ev_val = _ev(S, E, M, spec, plan), _ev(S, V, M, spec, plan)
    det["recent"] = {"2024-26 exam": ev_exam, "2022-23": ev_val}
    if ev_exam is None or ev_exam <= 0:
        return "FLUKE", f"under the current simulator rules the unseen 2024-26 years do not pay out ({ev_exam}$/eval)", det
    if ev_val is None or ev_val <= 0:
        fails.append(f"2022-23 does not pay out ({ev_val}$/eval) - only one recent stretch works")
    # 1b. the LATEST stretch (closest to the future): accounts started in the last ~6 months of data (leaving 60 days for
    #     them to play out) must pay out too - otherwise the recent profit came from an older stretch that already ended
    import prop_sim
    pts, worst, stop = S._prop_inputs(E, M); size = S._sizer(spec, stop)
    a0, a1 = max(0, len(pts) - 126 - 60), max(1, len(pts) - 60)       # ~6 months of start days
    last = prop_sim.evaluate(pts, worst, plan, size, starts=range(a0, a1, 1))
    det["latest_6m"] = {"accounts": last["accounts"], "pass_rate": last["pass_rate"], "share_with_payout": last["share_with_payout"], "ev": last["ev_per_eval"]}
    if last["ev_per_eval"] <= 0:
        fails.append(f"accounts started in the latest 6 months never made money (pass {last['pass_rate']:.0%}, "
                     f"{last['share_with_payout']:.0%} got a payout, EV {last['ev_per_eval']:+.0f}$/eval) - the profit came from an earlier stretch")
    # 2. luck on the unseen years
    evs = _placebo(S, D, M, spec, plan, E, reps, seed); p = float((evs >= ev_exam).mean())
    det["placebo_unseen"] = {"strategy_ev": round(ev_exam, 1), "random_mean_ev": round(float(evs.mean()), 1),
                             "random_p90_ev": round(float(np.percentile(evs, 90)), 1), "p": round(p, 3)}
    if p >= 0.10:
        return "FLUKE", (f"random entries with the same plan/sizing/stop/target on the unseen 2024-26 days pay about as much "
                         f"(random EV {evs.mean():+.0f} vs {ev_exam:+.0f}; p={p:.2f}) - the payouts come from the prop rules, not the strategy"), det
    # 3. lucky-number test on the recent years (the strategy itself stays fixed)
    res = {}
    for name, kw in {"stop -20%": dict(stop_mult=0.8), "stop +20%": dict(stop_mult=1.2),
                     "target -20%": dict(tgt_mult=0.8), "target +20%": dict(tgt_mult=1.2)}.items():
        res[name] = _ev(S, S.backtest(spec, X, recent, **kw), M, spec, plan)
    for dm in (-15, 15):
        if spec["entry"]["type"] == "time":
            sp = dict(spec, entry=dict(spec["entry"])); t = min(max(S.mins(sp["entry"]["at"]) + dm, 1), 380)
            sp["entry"]["at"] = f"{(510 + t) // 60:02d}:{(510 + t) % 60:02d}"
            res[f"entry {dm:+d} min"] = _ev(S, S.backtest(sp, X, recent), M, sp, plan)
        else:
            res[f"window {dm:+d} min"] = _ev(S, S.backtest(spec, X, recent, win_shift=dm), M, spec, plan)
    det["neighbours_2022_26"] = res; ok = sum(1 for v in res.values() if v is not None and v > 0)
    if ok < 4:
        fails.append(f"only the exact numbers work: {ok}/6 neighbouring settings pay out on 2022-26 - likely a lucky pick from the grid")
    # 3b. bold-play tell (expert review): an eval is a barrier payoff - without real drift, bigger size raises the pass rate.
    #     If the payouts vanish at half or a quarter of the risk, they come from variance, not from an edge.
    pr = dict(spec.get("prop") or {}); half = {}
    for f in (0.5, 0.25):
        sp = dict(spec, prop=dict(pr, risk=float(pr.get("risk", 0.25)) * f, eval_risk=float(pr.get("eval_risk", pr.get("risk", 0.25))) * f))
        half[f"{f}x risk"] = _ev(S, E, M, sp, plan)
    det["bold_play"] = half
    if half.get("0.5x risk") is not None and half["0.5x risk"] <= 0:
        fails.append(f"variance-driven: at half the risk the unseen years pay {half['0.5x risk']:+.0f}$/eval (bold-play tell)")
    # 3c. bootstrap account paths on the unseen years: the 20th percentile of the EV estimate must be > 0 (review upgrade 9e)
    try:
        import prop_sim
        pts_, w_, st_ = S._prop_inputs(E, M); bs = prop_sim.bootstrap(pts_, w_, plan, S._sizer(spec, st_)); det["bootstrap_exam"] = bs
        if bs and bs["ev_p20"] <= 0: fails.append(f"bootstrap: 20th percentile of the EV per eval is {bs['ev_p20']:+.0f}$ - could be noise")
    except Exception as e_:
        det["bootstrap_exam"] = f"skipped: {type(e_).__name__}"
    # 4. costs
    c = _ev(S, S.backtest(spec, X, exam, cost_mult=1.5), M, spec, plan); det["exam_costs_1.5x"] = c
    if c is None or c <= 0: fails.append(f"with 1.5x costs the unseen years pay {c}$/eval")
    # 5. no anti-edge in 2014-21 (dormant is fine, clearly worse than random is not)
    old = T[Ty <= 2021]; ev_old = _ev(S, old, M, spec, plan)
    base = _placebo(S, D, M, spec, plan, old, 20, seed + 1) if len(old) >= 30 else np.array([np.nan])
    b_lo = float(np.nanpercentile(base, 10)) if np.isfinite(base).any() else None
    det["old_2014_21"] = {"ev": ev_old, "random_mean": round(float(np.nanmean(base)), 1) if b_lo is not None else None, "random_p10": b_lo}
    if ev_old is not None and b_lo is not None and ev_old < b_lo:
        fails.append(f"2014-21 was clearly worse than random entries ({ev_old:+.0f} vs random 10th pct {b_lo:+.0f}$/eval) - an anti-edge, not a dormant one")
    if fails:
        return "FRAGILE", "; ".join(fails), det
    return "CONFIRMED", (f"pays out on 2024-26 ({ev_exam:+.0f}) and 2022-23 ({ev_val:+.0f}) under current rules, beats random entries "
                         f"on the unseen years (p={p:.2f}), {ok}/6 neighbouring settings pay, survives 1.5x costs ({c:+.0f}), "
                         f"2014-21 no worse than random ({ev_old if ev_old is None else round(ev_old)} vs {b_lo if b_lo is None else round(b_lo)})"), det


def review_entry(e):
    import test_engine as TE
    _, X = TE.frame()
    plan = (e.get("prop_exam") or {}).get("plan") or (e.get("prop") or [{}])[0].get("plan")
    label, why, det = review(e["spec"], X, plan)
    return {"review": f"{label} (auto v2, {pd.Timestamp.now(tz='UTC'):%Y-%m-%d}): {why}", "review_detail": det}


def regime_watch(e, F):
    """Called every evening for CONFIRMED strategies: compares the forward days (the 'coming weeks') with the recent
    regime. Demotes when the forward trades are clearly worse than the 2022-26 trades (one-sided t-test at 5%, after
    at least 15 forward trades). Returns a new review string or None."""
    import strategy_lab as S, test_engine as TE
    f = F[(F.id == S.spec_id(e["spec"])) & (F.traded)] if len(F) else F
    if len(f) < 15: return None
    _, X = TE.frame(); M = S.data(e["spec"].get("market"))["M"]
    base_from = "2025-04-01" if e.get("source") == "prop-search-recent" else "2022-01-01"
    rec = S.backtest(e["spec"], X, np.where(M.session >= base_from)[0]).R.values
    d = f.R.mean() - rec.mean(); se = np.sqrt(f.R.var(ddof=1) / len(f) + rec.var(ddof=1) / len(rec))
    if se > 0 and d / se < -1.645:
        return (f"FRAGILE (regime watch, {pd.Timestamp.now(tz='UTC'):%Y-%m-%d}): the last {len(f)} forward trades average "
                f"{f.R.mean():+.2f}R vs {rec.mean():+.2f}R in 2022-26 (t={d / se:.1f}) - the regime it relied on looks broken")
    return None


# ------------------------------------------------------------------ NEW-REGIME track (edges that may only exist since 2024)
RECENT_FROM, RECENT_VAL_FROM, FORWARD_MIN = "2024-01-01", "2025-04-01", 60     # sequential Bayesian forward test (expert review)
RECENT_EXAMS_PER_WEEK = 2


def recent_exam(spec, X, name, plan):
    """The 'exam' of a recent-track candidate (searched on 2024-01..2025-03, validated on 2025-04..now). No untouched
    years are left, so this is a strict review on the validation months - and the REAL exam is the coming weeks
    (forward test, see recent_forward). Writes an entry to strategies.jsonl and returns the verdict.
    Checks: (1) validation months pay out under current rules AND accounts started in the latest ~6 months pay;
    (2) beats random entries on the validation days (p < 0.05 - stricter than classic, few independent accounts);
    (3) lucky-number test on 2024-now (>= 4/6 neighbouring settings pay); (4) 1.5x costs still pay on the validation months;
    (5) 2014-2023 not clearly worse than random entries (dormant is fine, anti-edge is not)."""
    import json, strategy_lab as S, prop_sim
    from datetime import datetime, timezone
    wk = S._week(); fn = os.path.join(HERE, "knowledge", "prop_search", "recent", "exams_week.json")
    ex = json.load(open(fn)) if os.path.exists(fn) else {}
    if ex.get(wk, 0) >= RECENT_EXAMS_PER_WEEK:
        return "PASSED VALIDATION (recent track), WAITING FOR EXAM (weekly budget used up)"
    ex[wk] = ex.get(wk, 0) + 1; os.makedirs(os.path.dirname(fn), exist_ok=True); json.dump(ex, open(fn, "w"))
    D = S.data(spec.get("market")); M = D["M"]
    T = S.backtest(spec, X, np.arange(len(M)))
    V = T[T.session >= RECENT_VAL_FROM]; A = T[(T.session >= RECENT_FROM) & (T.session < RECENT_VAL_FROM)]
    det, fails = {}, []
    ev_v = _ev(S, V, M, spec, plan); det["validation"] = ev_v
    if ev_v is None or ev_v <= 0: fails.append(f"validation months pay {ev_v}$/eval")
    pts, worst, stop = S._prop_inputs(V, M); size = S._sizer(spec, stop)
    last = prop_sim.evaluate(pts, worst, plan, size, starts=range(max(0, len(pts) - 186), max(1, len(pts) - 60), 1)) if len(pts) > 80 else {"ev_per_eval": -1, "pass_rate": 0, "share_with_payout": 0, "accounts": 0}
    det["latest_6m"] = {k: last[k] for k in ("accounts", "pass_rate", "share_with_payout", "ev_per_eval")}
    if last["ev_per_eval"] <= 0: fails.append(f"accounts started in the latest ~6 months pay {last['ev_per_eval']:+.0f}$/eval")
    if not fails:
        evs = _placebo(S, D, M, spec, plan, V, 40, 5); p = float((evs >= ev_v).mean())
        det["placebo"] = {"random_mean_ev": round(float(evs.mean()), 1), "p": round(p, 3)}
        if p >= 0.05: fails.append(f"random entries on the same days pay about as much (random {evs.mean():+.0f} vs {ev_v:+.0f}, p={p:.2f})")
    if not fails:
        recent = np.where(M.session >= RECENT_FROM)[0]; res = {}
        for nm, kw in {"stop -20%": dict(stop_mult=0.8), "stop +20%": dict(stop_mult=1.2), "target -20%": dict(tgt_mult=0.8), "target +20%": dict(tgt_mult=1.2)}.items():
            res[nm] = _ev(S, S.backtest(spec, X, recent, **kw), M, spec, plan)
        for dm in (-15, 15):
            if spec["entry"]["type"] == "time":
                sp = dict(spec, entry=dict(spec["entry"])); t = min(max(S.mins(sp["entry"]["at"]) + dm, 1), 380)
                sp["entry"]["at"] = f"{(510 + t) // 60:02d}:{(510 + t) % 60:02d}"; res[f"entry {dm:+d}"] = _ev(S, S.backtest(sp, X, recent), M, sp, plan)
            else:
                res[f"window {dm:+d}"] = _ev(S, S.backtest(spec, X, recent, win_shift=dm), M, spec, plan)
        det["neighbours"] = res; ok = sum(1 for v in res.values() if v is not None and v > 0)
        if ok < 4: fails.append(f"only {ok}/6 neighbouring settings pay - a lucky pick of exact numbers")
        c = _ev(S, S.backtest(spec, X, np.where(M.session >= RECENT_VAL_FROM)[0], cost_mult=1.5), M, spec, plan); det["costs_1.5x"] = c
        if c is None or c <= 0: fails.append(f"1.5x costs pay {c}$/eval")
        old = T[T.session < RECENT_FROM]
        if len(old) >= 30:
            ev_o = _ev(S, old, M, spec, plan); b = _placebo(S, D, M, spec, plan, old, 20, 6); b_lo = float(np.nanpercentile(b, 10))
            det["old"] = {"ev": ev_o, "random_p10": round(b_lo, 1)}
            if ev_o is not None and ev_o < b_lo: fails.append(f"before 2024 it was clearly worse than random ({ev_o:+.0f} vs {b_lo:+.0f}) - an anti-edge")
    today = datetime.now(timezone.utc).date().isoformat()
    head = f"search 2024-01..2025-03: {len(A)} trades | validation 2025-04..now on {plan}: EV {ev_v if ev_v is None else round(ev_v)}$/eval"
    if fails:
        verdict = f"NOT CONFIRMED - failed the RECENT EXAM (recent track): {'; '.join(fails)}. {head}"
        review = None
    else:
        verdict = (f"PROMISING STRATEGY (recent track, passed the RECENT EXAM; final test = the coming weeks): {head}, "
                   f"latest 6 months {last['ev_per_eval']:+.0f}, beats random (p={det['placebo']['p']:.2f}), {ok}/6 neighbours, 1.5x costs {c:+.0f}")
        review = f"PENDING (recent track, forward 0/{FORWARD_MIN} trades, {today}): passed the recent exam - confirmed only if the coming weeks hold up"
    e = {"date": today, "name": name, "spec": spec, "source": "prop-search-recent", "verdict": verdict, "recent_exam": det}
    if review: e["review"] = review
    with open(S.LOG, "a") as f: f.write(json.dumps(e) + "\n")
    return verdict


def bayes_edge(R, sd=None, prior_sd=0.05):
    """Skeptical prior on the true mean R per trade: Normal(0, 0.05R). Updated with each forward trade (normal likelihood,
    per-trade sd from the trades themselves or the validation months). Returns (posterior mean, P(edge > 0))."""
    from statistics import NormalDist
    R = np.asarray(R, float); n = len(R)
    if n == 0: return 0.0, 0.5
    s2 = (sd if sd else max(np.std(R, ddof=1) if n > 1 else 1.0, 0.3)) ** 2
    prec = 1 / prior_sd ** 2 + n / s2; mu = (R.sum() / s2) / prec
    return float(mu), float(1 - NormalDist(mu, prec ** -0.5).cdf(0.0))


def recent_forward(e, F):
    """Every evening for PENDING recent-track strategies - sequential Bayesian test on the real forward trades:
    CONFIRMED when P(edge > 0) > 0.9 with at least FORWARD_MIN (60) trades; FRAGILE when P(edge > 0) < 0.1 (after >= 20
    trades) or no confirmation after 3x FORWARD_MIN trades. (The old 15-trade rule could not tell +0.1R from -0.1R.)"""
    import strategy_lab as S, test_engine as TE
    f = F[(F.id == S.spec_id(e["spec"])) & (F.traded)] if len(F) else F
    n = len(f); today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    sd = None
    try:
        _, X = TE.frame(); M = S.data(e["spec"].get("market"))["M"]
        v = S.backtest(e["spec"], X, np.where(M.session >= RECENT_VAL_FROM)[0]).R.values; sd = float(np.std(v, ddof=1)) if len(v) > 5 else None
    except Exception:
        pass
    mu, p = bayes_edge(f.R.values if n else [], sd)
    if n >= FORWARD_MIN and p > 0.9:
        return f"CONFIRMED (recent track, forward, {today}): {n} real forward trades, posterior edge {mu:+.3f}R, P(edge > 0) = {p:.0%}"
    if (n >= 20 and p < 0.1) or n >= 3 * FORWARD_MIN:
        return f"FRAGILE (recent track, forward, {today}): {n} forward trades, posterior edge {mu:+.3f}R, P(edge > 0) = {p:.0%} - the coming weeks did not hold up"
    return f"PENDING (recent track, forward {n}/{FORWARD_MIN}+ trades, P(edge > 0) {p:.0%}, {today}): confirmed only if the coming weeks hold up"


if __name__ == "__main__":                                     # review every exam-passer without a review (--all: re-review all)
    import json, strategy_lab as S
    L = [json.loads(l) for l in open(S.LOG) if l.strip()]; RV = load_reviews()
    for e in L:
        x = effective(e, RV)
        if str(e.get("verdict", "")).startswith("PROMISING STRATEGY") and e.get("source") != "family" and isinstance(e.get("spec"), dict) \
                and e["spec"].get("kind", "strategy") == "strategy" and ("--all" in sys.argv or not x.get("review")):
            r = review_entry(e); save_review(e, **r); print(e["name"][:70], "->", r["review"][:500])
