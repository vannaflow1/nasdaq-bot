"""families.py - mechanism families (expert review, 21 Oct 2026, upgrade 2).

Instead of discovering thousands of single specs (where the luck bar rises as fast as the search), Volta tests a small
number of PRE-REGISTERED families. Each family = a one-sentence mechanism + a fixed grid of 20-50 variants, frozen in git
before its validation years are ever looked at. One family statistic decides:
    the MEDIAN validation edge (mean net R per trade on 2022-23) across ALL variants,
compared with a placebo family on the same days (null v3 since 22 Oct 2026: every trade re-entered with its side
reversed, or at a random minute when the side is known before the session - ONE random draw per market-session shared
by all variants, 20,000 draws, exact randomization p; see null_draws and knowledge/frozen/null_v3.json).
A real mechanism shows up as a plateau (most variants pay); luck shows up as a spike (one variant).
Multiplicity: every family ever scored is in the ledger (knowledge/families_ledger.csv); a family passes only if its
p-value < 0.05 / (number of families scored so far, itself included) AND its median validation edge > 0 AND >= 60% of
its variants have a positive validation edge.
A passing family's best variant (chosen on the SEARCH years 2014-21 only, by bootstrap lower bound) takes the locked exam
(counts toward the weekly exam cap): edge on 2024-now > 0 with 90% confidence, then priced in the prop simulator.
Its verdict goes to strategies.jsonl with source "family"; Claude's nightly session reviews it.

A family in knowledge/families.json:
  {"id": "F5", "name": "...", "mechanism": "...", "citation": "...", "status": "registered" | "scored",
   "frozen": "<git commit>", "sleeve": [<spec>, ...]   (specs traded together = one variant; usually one spec),
   "grid": {"<dotted path>": [values, ...], ...}       (applied to every spec in the sleeve that has the path)}
Run: python families.py [--id F5] [--reps 100]"""
import copy, itertools, json, os, random, subprocess, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
REG, LEDGER = os.path.join(K, "families.json"), os.path.join(K, "families_ledger.csv")
A_END, B_END = "2021-12-31", "2023-12-31"
MAX_VARIANTS, ALPHA = 50, 0.05


def _set(d, path, v):
    ks = path.split("."); x = d
    for k in ks[:-1]:
        if k not in x: return False
        x = x[k]
    if ks[-1] not in x and len(ks) > 1 and ks[-2] not in ("prop", "manage"): return False
    x[ks[-1]] = v; return True


def variants(fam, seed=0):
    """Grid keys: "param.NAME" substitutes {NAME} anywhere in the sleeve's text; any other key is a spec path set on every
    spec of the sleeve that has it (e.g. "stop", "target", "exit", "manage")."""
    keys = list(fam["grid"]); combos = list(itertools.product(*[fam["grid"][k] for k in keys]))
    if len(combos) > MAX_VARIANTS: combos = random.Random(seed).sample(combos, MAX_VARIANTS)
    out = []
    for c in combos:
        txt = json.dumps(fam["sleeve"])
        for k, v in zip(keys, c):
            if k.startswith("param."): txt = txt.replace("{" + k[6:] + "}", str(v))
        sleeve = json.loads(txt)
        for sp in sleeve:
            sp.setdefault("kind", "strategy")
            for k, v in zip(keys, c):
                if k.startswith("param."): continue
                if k in ("manage",):
                    sp.pop("manage", None)
                    if v: sp["manage"] = v
                else: _set(sp, k, v)
        if fam.get("markets"):                                  # v2 pooled family: the same frozen sleeve on every listed market
            sleeve = [dict(copy.deepcopy(sp), market=m) for m in fam["markets"] for sp in sleeve]
        out.append({"params": dict(zip(keys, c)), "sleeve": sleeve})
    return out


def fam_hash(fam):
    import hashlib
    h = {"sleeve": fam["sleeve"], "grid": fam["grid"]}
    for k in ("markets", "rules", "sealed", "forward_source", "statistic", "contrast", "window"):                             # v2: the market list and rule set are frozen too
        if fam.get(k): h[k] = fam[k]
    return hashlib.sha1(json.dumps(h, sort_keys=True).encode()).hexdigest()[:12]


def trades(S, X, sleeve, lo, hi):
    """All trades of a sleeve between dates lo..hi (sessions), with the market for each."""
    rows = []
    for sp in sleeve:
        M = S.data(sp.get("market"))["M"]; idx = np.where((M.session >= lo) & (M.session <= hi))[0]
        T = S.backtest(sp, X, idx)
        if len(T): rows.append(T.assign(market=sp.get("market", "NQ"), spec=json.dumps(sp)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["session", "i", "pnl", "R", "side", "k", "market", "spec"])


NULL_REPS = int(os.environ.get("NULL_REPS", 20000))
MINUTE_BINS = 16


def twin_tables(S, T, minute_bins=MINUTE_BINS):
    """NULL v3 (22 Oct 2026, knowledge/frozen/null_v3.json). For every trade of T: R1 = its real result, R0 = the same
    minute with the side REVERSED, and - only when the side is known before the session - Rm[:, b] = the same side at the
    b-th of `minute_bins` evenly spaced minutes of its entry window. Simulated once; each null draw then only picks columns.
    key = market|session: the unit that gets ONE shared random draw in every null world."""
    n = len(T); R1 = T.R.to_numpy(float); R0 = np.full(n, np.nan); Rm = None
    key = (T.market.astype(str) + "|" + T.session.astype(str)).to_numpy() if n else np.array([], dtype=object)
    pos = {ix: j for j, ix in enumerate(T.index)}
    for spec_s, g in T.groupby("spec", sort=False):
        sp = json.loads(spec_s); D = S.data(sp.get("market")); e = sp["entry"]; intraday = intraday_side(sp)
        lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
        hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(sp.get("exit", "14:55")) - 5, 380)
        lo, hi = max(lo, 1), max(hi, lo + 2)
        if not intraday and Rm is None: Rm = np.full((n, minute_bins), np.nan)
        for ix, i, k, sd in zip(g.index, g.i.values, g.k.values, g.side.values):
            j = pos[ix]
            r = S.simulate_session(D, int(i), sp, entry_override=(int(k), -int(sd)))
            R0[j] = r[1] if r else np.nan
            if not intraday:                                   # side decided during the session: a random EARLIER minute with
                for b in range(minute_bins):                   # that side would use the future -> reversed-side twins only
                    r = S.simulate_session(D, int(i), sp, entry_override=(int(lo + (b + 0.5) * (hi - lo) / minute_bins), int(sd)))
                    Rm[j, b] = r[1] if r else np.nan
    return {"R1": R1, "R0": R0, "Rm": Rm, "key": key}


def null_draws(tabs, stat, reps=NULL_REPS, seed=7):
    """Null distribution of a family statistic. ONE random draw per market-session, SHARED by every variant: the variants
    are near-copies of one signal (median pairwise correlation of their daily R ~0.4 on F2), so a no-edge world must move
    them together. The old null drew independent coins per variant; averaging those across 50 variants made it 3-4x too
    narrow (measured 22 Oct 2026 on F1, F2, F10, F11, F12) - every p-value was too small and F11 passed only because of it.
    Even draws: same minute, side reversed on a random half of the sessions (an exact sign-flip randomization test of
    "the direction carries no information"). Odd draws, where the side is known before the session: same side, one random
    minute per session (timing carries no information). stat(xs) -> family statistic, xs[v] = variant v's R per trade."""
    rng = np.random.default_rng(seed)
    keys = sorted(set().union(*[set(t["key"]) for t in tabs])); kp = {k: j for j, k in enumerate(keys)}
    for t in tabs: t["ki"] = np.array([kp[k] for k in t["key"]], int)
    has_m = any(t["Rm"] is not None for t in tabs); out = np.empty(reps)
    for r in range(reps):
        c = rng.random(len(keys)) < 0.5
        mb = rng.integers(0, MINUTE_BINS, len(keys)) if (has_m and r % 2 == 1) else None
        xs = []
        for t in tabs:
            x = np.where(c[t["ki"]], t["R0"], t["R1"])
            if mb is not None and t["Rm"] is not None:
                xm = t["Rm"][np.arange(len(x)), mb[t["ki"]]]; x = np.where(np.isfinite(xm), xm, x)
            xs.append(x)
        out[r] = stat(xs)
    return out


def null_p(obs, null):
    """Randomization p-value: (1 + draws at least as extreme) / (1 + draws) - never 0, resolution 1/(reps+1)."""
    null = np.asarray(null, float); null = null[np.isfinite(null)]
    return float((1 + np.sum(null >= obs)) / (1 + len(null)))


def intraday_side(sp):
    """True when a spec's direction is only known during the session (own:day, schedules, OCO brackets)."""
    e = sp.get("entry", {})
    return e.get("type") in ("schedule", "oco") or str(e.get("side", "")).lstrip("-").startswith("own:day") or str(e.get("side", "")) in ("own:day", "own:-day")


def ledger():
    return pd.read_csv(LEDGER) if os.path.exists(LEDGER) else pd.DataFrame()


def _day_feature(S, X, T, feat):
    """Value of a known-at-the-open feature (X keyed by memory date) for each trade's session."""
    if not len(T): return np.array([])
    vals = []
    for mk, g in T.groupby("market"):
        M = S.data(mk)["M"]; dm = dict(zip(M.session, M.date))
        f = X[feat].reindex(pd.to_datetime(g.session.map(dm))).to_numpy(); vals.append(pd.Series(f, index=g.index))
    return pd.concat(vals).reindex(T.index).to_numpy(float)


def score_contrast(fam, X, S, reps=100, seed=7):
    """Expert review 3 (F11): a pre-registered CONTRAST - median over variants of (edge on low-feature days - edge on
    high-feature days) inside one window; placebo family = coin-flip twins of the same trades, split the same way."""
    import sealed as SE
    from statistics import NormalDist
    c = fam["contrast"]; lo_w, hi_w = fam["window"]; V = variants(fam); rng = np.random.default_rng(seed); rows, keep = [], []
    for v in V:
        T = trades(S, X, v["sleeve"], lo_w, hi_w); f = _day_feature(S, X, T, c["feature"])
        lo_m = (f >= c["low"][0]) & (f <= c["low"][1]); hi_m = (f >= c["high"][0]) & (f <= c["high"][1])
        if lo_m.sum() < 20 or hi_m.sum() < 20: continue
        rows.append({"params": json.dumps(v["params"]), "n_low": int(lo_m.sum()), "n_high": int(hi_m.sum()),
                     "edge_low": float(T.R[lo_m].mean()), "edge_high": float(T.R[hi_m].mean()),
                     "contrast": float(T.R[lo_m].mean() - T.R[hi_m].mean())})
        keep.append((T, lo_m, hi_m))
    R = pd.DataFrame(rows)
    if len(R) < 5: return {"verdict": "TOO FEW TRADES", "variants": len(V), "usable": len(R)}, R, V
    med = float(R.contrast.median()); share = float((R.contrast > 0).mean())
    tabs = [twin_tables(S, T) for T, _, _ in keep]                 # null v3: the reversed-side twin of every trade, simulated once
    for t in tabs: t["Rm"] = None                                  # a contrast asks about direction only: sign-flip draws
    masks = [(lo_m, hi_m) for _, lo_m, hi_m in keep]
    pl = null_draws(tabs, lambda xs: float(np.median([np.nanmean(x[a]) - np.nanmean(x[b]) for x, (a, b) in zip(xs, masks)])), seed=seed)
    p = null_p(med, pl)
    L = ledger(); j = int((L.get("rules", pd.Series(dtype=str)).astype(str) == "v2").sum()) + 1 if len(L) else 1
    alpha = SE.alpha_v2(j); passed = med > 0 and share >= 0.6 and p < alpha
    return {"variants": len(V), "usable": len(R), "median_edge_A": round(float(R.edge_low.median()), 4),
            "median_edge_B": round(float(R.edge_high.median()), 4), "median_contrast": round(med, 4), "share_positive_B": round(share, 3),
            "placebo_median_mean": round(float(pl.mean()), 4), "p": round(p, 5), "families_scored": len(L) + 1,
            "alpha": round(alpha, 5), "passed": bool(passed), "rules": "v2", "null": "v3-shared",
            "verdict": (f"{'PASSED' if passed else 'FAILED'} (contrast test): median low-minus-high {c['feature']} edge {med:+.3f}R, "
                        f"{share:.0%} of variants positive, placebo {pl.mean():+.3f}R, p={p:.4f} vs alpha {alpha:.4f} "
                        "(median_edge_A/B columns = low/high-day edges)")}, R, V


def score_family(fam, X, S, reps=100, seed=7):
    if fam.get("statistic") == "contrast": return score_contrast(fam, X, S, reps, seed)
    if fam.get("rules") == "v2": reps = min(reps, int(os.environ.get("V2_REPS", 100)))   # measured: ~0.3h for 50 variants x 3 markets
    import prop_search as PS
    V = variants(fam); rng = np.random.default_rng(seed); rows = []
    v2 = fam.get("rules") == "v2"; b_end = "2099-12-31" if v2 else B_END   # v2: 2024-now is validation (it is spent as an exam)
    TB_all = []
    for v in V:
        TA = trades(S, X, v["sleeve"], "1900-01-01", A_END); TB = trades(S, X, v["sleeve"], "2022-01-01", b_end)
        ea = PS.edge_stats(TA.R.values) if len(TA) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan, "edge_t": np.nan}
        eb = PS.edge_stats(TB.R.values, seed=1) if len(TB) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan, "edge_t": np.nan}
        rows.append({"params": json.dumps(v["params"]), "n_A": ea["n"], "edge_A": ea["edge"], "lb10_A": ea["edge_lb10"],
                     "n_B": eb["n"], "edge_B": eb["edge"], "lb10_B": eb["edge_lb10"]})
        TB_all.append(TB)
    R = pd.DataFrame(rows); ok = R[R.n_B >= 20]
    if len(ok) < 5:
        return {"verdict": "TOO FEW TRADES", "variants": len(V), "usable": len(ok)}, R, V
    med_B = float(ok.edge_B.median()); share_pos = float((ok.edge_B > 0).mean()); med_A = float(R[R.n_A >= 20].edge_A.median())
    tabs = [twin_tables(S, TB_all[i]) for i in ok.index]      # null v3: shared draws per market-session (see null_draws)
    pl = null_draws(tabs, lambda xs: float(np.median([np.nanmean(x) for x in xs])), seed=seed)
    p = null_p(med_B, pl)                                    # exact randomization p (20,000 draws resolve alphas down to ~1e-4)
    L = ledger(); k = (len(L) + 1)
    if v2:
        import sealed as SE
        j = int((L.get("rules", pd.Series(dtype=str)).astype(str) == "v2").sum()) + 1 if len(L) else 1
        alpha = SE.alpha_v2(j)
    else:
        alpha = ALPHA / k
    passed = med_B > 0 and share_pos >= 0.6 and p < alpha
    res = {"variants": len(V), "usable": len(ok), "median_edge_A": round(med_A, 4), "median_edge_B": round(med_B, 4),
           "share_positive_B": round(share_pos, 3), "placebo_median_mean": round(float(pl.mean()), 4) if len(pl) else None,
           "p": round(p, 5), "families_scored": k, "alpha": round(alpha, 5), "passed": bool(passed), "rules": "v2" if v2 else "v1",
           "null": "v3-shared"}
    return res, R, V


def exam_family(fam, R, V, X, S):
    """Best variant chosen on the SEARCH years only (bootstrap lower bound), then the locked exam on 2024-now."""
    import prop_search as PS, prop_sim
    best_i = int(R.lb10_A.fillna(-9).idxmax()); v = V[best_i]
    if not S.spend_exam(f"family {fam['id']}", "family"):
        return v, "PASSED THE FAMILY TEST, WAITING FOR EXAM (weekly exam budget used up)", {}
    TE_ = trades(S, X, v["sleeve"], S.EXAM_FROM, "2099-12-31"); ee = PS.edge_stats(TE_.R.values, seed=2) if len(TE_) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan, "edge_t": np.nan}
    det = {"exam_edge": ee}
    if not (ee["n"] >= 30 and np.isfinite(ee["edge_lb10"]) and ee["edge_lb10"] > 0):
        return v, f"NOT CONFIRMED - failed the locked exam (family): edge on 2024-now {ee['edge']:+.3f}R (90% lower bound {ee['edge_lb10']:+.3f}R, {ee['n']} trades)", det
    # price it: one account trading the whole sleeve (same-day trades summed; that day's worst = every trade at its stop)
    M = S.data(v["sleeve"][0].get("market"))["M"]
    g = TE_.groupby("session").agg(pnl=("pnl", "sum"), R=("R", "sum")).reset_index()
    g["R"] = g.pnl / (TE_.assign(st=TE_.pnl / TE_.R.replace(0, np.nan)).groupby("session").st.apply(lambda s: s.abs().sum()).reindex(g.session).values)
    spec0 = dict(v["sleeve"][0], prop={"risk": 0.2, "eval_risk": 0.35})
    pr = S.prop_score(g, M, spec0)[0]; det["priced"] = pr
    try:
        import prop_sim
        pts_, w_, st_ = S._prop_inputs(g, M); det["bootstrap"] = prop_sim.bootstrap(pts_, w_, pr["plan"], S._sizer(spec0, st_))
    except Exception as e_:
        det["bootstrap"] = f"skipped: {type(e_).__name__}"
    return v, (f"PROMISING STRATEGY (family {fam['id']}, passed the locked exam): edge on 2024-now {ee['edge']:+.3f}R "
               f"(90% lower bound {ee['edge_lb10']:+.3f}R, {ee['n']} trades); priced on {pr['plan']}: pass {pr['pass_rate']:.0%}, "
               f"EV {pr['ev_per_eval']:+.0f}$/eval"), det


def exam_family_v2(fam, R, V, X, S, res):
    """v2: best variant on the search years; its never-seen SEALED window (Feb-Oct 2026) is spent ONCE as the first block of
    a group-sequential test; every day after the freeze date adds to it (forward_route). Nothing is wasted: an exam
    that alone would be underpowered still counts as evidence (expert review 2, power-gated route - see sealed.py)."""
    import sealed as SE
    best_i = int(R.lb10_A.fillna(-9).idxmax()); v = V[best_i]
    TB = trades(S, X, v["sleeve"], "2022-01-01", "2099-12-31"); val = SE.edge_days(TB, seed=3)
    days_pm = {m: int(g.session.nunique()) for m, g in TB.groupby("market")} if len(TB) else {}
    mkts = sorted({(sp.get("market") or "NQ").upper() for sp in v["sleeve"]})
    se_x, n_days = SE.expected_exam_se(val, days_pm, mkts); shrunk = 0.5 * float(res.get("median_edge_B") or 0)
    det = {"validation": val, "exam_se_expected": se_x, "sealed_days": n_days, "shrunk_edge": shrunk,
           "power_sealed_alone": round(SE.exam_power(shrunk, se_x), 3), "markets": mkts, "route": "forward"}
    if fam.get("sealed") is False:                            # proxy too far from this market's futures (calibration): no
        det["route"] = "forward"                              # sealed block; real futures days from the archive only
        return v, (f"PASSED THE FAMILY TEST -> FORWARD ROUTE on real futures bars (no sealed block: the free proxy does not "
                   f"reproduce this family's trades well enough); group-sequential test from {fam.get('registered')}"), det
    if not S.spend_exam(f"family {fam['id']} (sealed window)", "family"):
        return v, "PASSED THE FAMILY TEST, WAITING FOR EXAM (weekly exam budget used up)", det
    dec, st = SE.forward_decision(SE.proxy_trades(S, X, v["sleeve"]))
    det["sealed"] = {k: st.get(k) for k in ("n", "days", "edge", "z", "look", "boundary")}
    if dec == "CONFIRMED":
        det["route"] = "done"
        return v, (f"PROMISING STRATEGY (family {fam['id']}, CONFIRMED on the sealed never-seen window alone: edge {st['edge']:+.3f}R, "
                   f"z {st['z']:.2f} >= {st['boundary']}, {st['n']} trades on {st['days']} days)"), det
    return v, (f"PASSED THE FAMILY TEST -> FORWARD ROUTE: sealed window gave {st['edge']:+.3f}R (z {st['z']:.2f}, {st['n']} trades); "
               f"every new day adds to its group-sequential test (up to {SE.N_MAX} trades, O'Brien-Fleming)"), det


def forward_route(fam, X, S):
    """Daily: the family's frozen variant on its sealed window PLUS every day after its freeze date (proxy feed, recomputed
    each run - sealed results are never stored per day), group-sequential decision on all of it."""
    import sealed as SE
    V = variants(fam); v = V[int(fam["forward_variant"])]
    lo = (pd.Timestamp(fam["registered"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    hi = (datetime.now(timezone.utc).date() - pd.Timedelta(days=1)).isoformat()
    parts = [] if fam.get("sealed") is False else [SE.proxy_trades(S, X, v["sleeve"])]
    if hi >= lo:
        parts.append(SE.archive_trades(S, X, v["sleeve"], lo, hi) if fam.get("forward_source") == "futures"
                     else SE.proxy_trades(S, X, v["sleeve"], lo=lo, hi=hi))
    if not parts: return "WAITING", {"n": 0}
    fd = os.path.join(K, "frozen", f"{fam['id']}_forward_design.json")
    if os.path.exists(fd):                                     # expert review 3: futility-first design, frozen before day 1
        T = pd.concat(parts, ignore_index=True)
        return SE.forward_decision_v3(T[T.session >= lo], json.load(open(fd)))
    return SE.forward_decision(pd.concat(parts, ignore_index=True))


def main():
    import strategy_lab as S, test_engine as TE
    only = sys.argv[sys.argv.index("--id") + 1] if "--id" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 100
    F = json.load(open(REG)) if os.path.exists(REG) else []
    _, X = TE.frame(); out_lines = []
    for fam in F:                                             # families that passed but met a full exam week: exam only
        if fam.get("status") != "awaiting_exam" or (only and fam["id"] != only): continue
        R = pd.read_csv(os.path.join(K, "research_out", f"family_{fam['id']}.csv")); V = variants(fam)
        if fam.get("rules") == "v2":
            L0 = ledger(); r0 = L0[L0.family == fam["id"]].iloc[-1].to_dict()
            v, verdict, det = exam_family_v2(fam, R, V, X, S, r0)
            if det.get("route") == "forward": fam["forward_variant"] = V.index(v); fam["status"] = "forward"
        else:
            v, verdict, det = exam_family(fam, R, V, X, S)
        if "WAITING FOR EXAM" in verdict: print(fam["id"], "still waiting for an exam slot"); continue
        today = datetime.now(timezone.utc).date().isoformat()
        e = {"date": today, "name": f"family {fam['id']}: {fam['name']} {v['params']}", "spec": v["sleeve"][0] if len(v["sleeve"]) == 1 else {"sleeve": v["sleeve"]},
             "source": "family", "family": fam["id"], "verdict": verdict, "exam_detail": json.loads(json.dumps(det, default=float))}
        if verdict.startswith("PROMISING STRATEGY"):
            e["review"] = f"PENDING (auto family exam, {today}): passed the family test and the locked exam - waiting for Claude's review"
        with open(S.LOG, "a") as f: f.write(json.dumps(e, default=float) + "\n")
        L = ledger(); L.loc[L.family == fam["id"], "verdict"] = str(verdict)[:300]; L.to_csv(LEDGER, index=False)
        fam["status"] = "scored"; fam["exam_date"] = today
        out_lines.append(f"{fam['id']} {fam['name']}: locked exam -> {verdict[:220]}"); print(out_lines[-1])
    for fam in F:                                             # v2 forward route: group-sequential check on the new days
        if fam.get("status") != "forward" or (only and fam["id"] != only): continue
        try:
            dec, st = forward_route(fam, X, S)
        except Exception as e_:
            print(fam["id"], "forward check failed:", type(e_).__name__, e_); continue
        fam["forward"] = {"date": datetime.now(timezone.utc).date().isoformat(), "decision": dec,
                          **{k: (round(v_, 4) if isinstance(v_, float) else v_) for k, v_ in st.items() if k != "bounds"}}
        print(fam["id"], "forward route:", dec, {k: st.get(k) for k in ("n", "days", "edge", "z", "look", "boundary")})
        if dec in ("CONFIRMED", "NOT CONFIRMED", "STOPPED (futility)"):
            today = datetime.now(timezone.utc).date().isoformat(); v = variants(fam)[int(fam["forward_variant"])]
            verdict = (f"PROMISING STRATEGY (family {fam['id']}, CONFIRMED by the group-sequential forward test: edge {st['edge']:+.3f}R, "
                       f"z {st['z']:.2f} >= {st.get('boundary')}, {st['n']} trades on {st['days']} days)" if dec == "CONFIRMED" else
                       f"NOT CONFIRMED - forward route {dec.lower()}: edge {st['edge']:+.3f}R, z {st['z']:.2f}, {st['n']} trades")
            e = {"date": today, "name": f"family {fam['id']}: {fam['name']} {v['params']}", "spec": v["sleeve"][0] if len(v["sleeve"]) == 1 else {"sleeve": v["sleeve"]},
                 "source": "family", "family": fam["id"], "verdict": verdict, "exam_detail": json.loads(json.dumps(st, default=float))}
            if dec == "CONFIRMED": e["review"] = f"PENDING (auto family forward route, {today}): waiting for Claude's review"
            with open(S.LOG, "a") as f: f.write(json.dumps(e, default=float) + "\n")
            L = ledger(); L.loc[L.family == fam["id"], "verdict"] = verdict[:300]; L.to_csv(LEDGER, index=False)
            fam["status"] = "scored"; out_lines.append(f"{fam['id']} {fam['name']}: {verdict[:220]}")
    for fam in F:
        if fam.get("status") != "registered" or (only and fam["id"] != only): continue
        if not fam.get("frozen") or fam.get("hash") != fam_hash(fam):
            print(fam["id"], "not frozen or changed after registration - skipped"); continue
        t0 = time.time()
        res, R, V = score_family(fam, X, S, reps=reps)
        verdict, det = res.get("verdict", "PASSED" if res.get("passed") else "FAILED"), {}
        if fam.get("statistic") == "contrast":
            pass                                              # an explanatory test: verdict only, no exam / forward route
        elif res.get("passed"):
            if fam.get("rules") == "v2": v, verdict, det = exam_family_v2(fam, R, V, X, S, res)
            else: v, verdict, det = exam_family(fam, R, V, X, S)
            if fam.get("rules") == "v2" and det.get("route") == "forward":
                fam["forward_variant"] = V.index(v)
            today = datetime.now(timezone.utc).date().isoformat()
            e = {"date": today, "name": f"family {fam['id']}: {fam['name']} {v['params']}", "spec": v["sleeve"][0] if len(v["sleeve"]) == 1 else {"sleeve": v["sleeve"]},
                 "source": "family", "family": fam["id"], "verdict": verdict, "family_test": res, "exam_detail": json.loads(json.dumps(det, default=float))}
            if verdict.startswith("PROMISING STRATEGY"):
                e["review"] = f"PENDING (auto family exam, {today}): passed the family test and the locked exam - waiting for Claude's review"
            with open(S.LOG, "a") as f: f.write(json.dumps(e, default=float) + "\n")
        row = dict(family=fam["id"], name=fam["name"], date=datetime.now(timezone.utc).date().isoformat(), frozen=fam["frozen"],
                   verdict=str(verdict)[:300], **{k: v for k, v in res.items() if k != "verdict"})
        L = ledger(); pd.concat([L, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)
        os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
        R.to_csv(os.path.join(K, "research_out", f"family_{fam['id']}.csv"), index=False)
        fam["status"] = ("awaiting_exam" if "WAITING FOR EXAM" in str(verdict) else
                         "forward" if "FORWARD ROUTE" in str(verdict) else "scored"); fam["scored"] = row["date"]
        out_lines.append(f"{fam['id']} {fam['name']}: median edge 2014-21 {res.get('median_edge_A')}, 2022-23 {res.get('median_edge_B')}R, "
                         f"{res.get('share_positive_B')} of variants positive, placebo p={res.get('p')} (need < {res.get('alpha')}) -> {str(verdict)[:200]}")
        print(out_lines[-1], f"({time.time() - t0:.0f}s)")
    json.dump(F, open(REG, "w"), indent=1)
    if out_lines:
        import test_engine as TE2
        ann = json.load(open(TE2.ANN)) if os.path.exists(TE2.ANN) else []
        ann.append({"title": "🧬 Family test results", "body": "\n".join(out_lines)[:1800]}); json.dump(ann, open(TE2.ANN, "w"), indent=1)
        s = json.load(open(os.path.join(HERE, "status.json"))) if os.path.exists(os.path.join(HERE, "status.json")) else {}
        L = ledger()
        s["families"] = ["MECHANISM FAMILIES (family = mechanism + 20-50 variants; passes only as a plateau beating a placebo family, "
                         "with a multiplicity-corrected p-value):"] + [f"- {r.family} {r['name']}: {r.verdict[:160]} (p={r.p}, median 2022-23 {r.median_edge_B}R)"
                                                                   for _, r in L.tail(12).iterrows()]
        json.dump(s, open(os.path.join(HERE, "status.json"), "w"), indent=1)


def register(fam):
    """Add a family and freeze it at the current commit (call before its validation years are looked at)."""
    F = json.load(open(REG)) if os.path.exists(REG) else []
    if any(f["id"] == fam["id"] for f in F): raise ValueError("family id exists")
    fam.setdefault("status", "registered"); fam["registered"] = datetime.now(timezone.utc).date().isoformat()
    for v in variants(fam):                                    # every variant must be a valid spec
        import strategy_lab as S
        for sp in v["sleeve"]: S.validate(sp)
    fam["hash"] = fam_hash(fam)
    fam["frozen"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip() or "unknown"
    F.append(fam); json.dump(F, open(REG, "w"), indent=1)


if __name__ == "__main__":
    main()
