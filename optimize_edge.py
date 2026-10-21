"""optimize_edge.py - once Volta has a CONFIRMED edge, try to make it better - without fooling itself (owner, 21 Oct 2026).

Champion / challenger, like the monthly brain retrain:
  1. A fixed, pre-declared set of REFINEMENTS of the confirmed strategy (stop and target +-, trade management, entry timing,
     one extra regime filter, schedule spacing / band width) is scored ONLY on the strategy's SEARCH years
     (classic + families: 2014-21; new-regime track: 2024-01..2025-03). The locked exam years are never used to choose.
  2. The best refinement must beat the original's bootstrap lower bound on those years by a margin AND must not be worse
     on the validation years (non-inferiority, never "improve on validation" - that would be fitting it).
  3. The account playbook (sizing: base risk levels, eval_finish, funded_micros) is chosen the same way, on the search years
     by prop EV, with the bootstrap 20th percentile > 0.
  4. The winner becomes a CHALLENGER: it is forward-traded every evening next to the CHAMPION (same days). Only when the
     forward trades prove it better (Bayesian test on the per-trade difference, P > 0.9 after >= 60 trades each) is it
     promoted; if it is clearly not better (P < 0.1, or 180 trades without proof) it is dropped. The champion keeps trading
     until then. Nothing about the champion's own verdict changes on the way.
State: knowledge/optimizations.json. Runs inside strategy_forward.py every evening (cheap: ~25 backtests per new champion)."""
import json, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
OPT = os.path.join(K, "optimizations.json")
EXTRA_FILTERS = ["vix - mean(vix, 60)", "mean(vix, 60) - vix", "rank(impl, 252) - 0.67", "0.33 - rank(impl, 252)",
                 "0.5 - k_red_any", "0.5 - gex_rank", "gex_rank - 0.5"]
MARGIN = 0.01                     # R per trade the refinement must add to the lower bound on the search years
MIN_FWD, MAX_FWD = 60, 180


def _load():
    try: return json.load(open(OPT))
    except Exception: return {}


def windows(e):
    if e.get("source") == "prop-search-recent":
        return ("2024-01-01", "2025-03-31"), ("2025-04-01", "2099-12-31")
    return ("1900-01-01", "2021-12-31"), ("2022-01-01", "2023-12-31")


def refinements(spec):
    """The pre-declared refinement set: (label, spec)."""
    import copy, strategy_lab as S
    out = []; e = spec["entry"]
    def add(lbl, sp):
        try: S.validate(sp); out.append((lbl, sp))
        except Exception: pass
    st = spec["stop"]
    for f in (0.8, 1.25):
        sp = copy.deepcopy(spec)
        if "points" in st: sp["stop"] = {"points": round(float(st["points"]) * f, 2)}
        elif "range" in st: sp["stop"] = {"range": round(float(st["range"]) * f, 3)}
        else: continue
        add(f"stop x{f}", sp)
    tg = spec["target"]
    for f in (0.75, 1.5):
        sp = copy.deepcopy(spec)
        if "R" in tg: sp["target"] = {"R": round(float(tg["R"]) * f, 2)}
        elif "range" in tg: sp["target"] = {"range": round(float(tg["range"]) * f, 3)}
        else: continue
        add(f"target x{f}", sp)
    for mg in [None, {"be_at_R": 0.5}, {"be_at_R": 1.0}, {"trail_R": 1.0}, {"partial": {"at_R": 1.0, "frac": 0.5}}]:
        if mg == spec.get("manage"): continue
        sp = copy.deepcopy(spec); sp.pop("manage", None)
        if mg: sp["manage"] = mg
        add(f"manage {mg}", sp)
    if e["type"] == "time":
        for dm in (-30, -15, 15, 30):
            sp = copy.deepcopy(spec); t = S.mins(e["at"]) + dm
            if 1 <= t <= 380: sp["entry"]["at"] = f"{(510 + t) // 60:02d}:{(510 + t) % 60:02d}"; add(f"entry {dm:+d} min", sp)
    if e["type"] == "schedule":
        for ev in (15, 30, 60):
            if int(e.get("every_min", 30)) != ev: sp = copy.deepcopy(spec); sp["entry"]["every_min"] = ev; add(f"check every {ev} min", sp)
        for dm in (-0.2, 0.2):
            sp = copy.deepcopy(spec); sp["entry"]["mult"] = round(float(e.get("mult", 1.0)) + dm, 2); add(f"band x{dm:+.1f}", sp)
    for f in EXTRA_FILTERS:
        sp = copy.deepcopy(spec)
        sp["filter"] = f"where({spec['filter']} > 0, {f}, -1)" if spec.get("filter") else f
        add(f"+filter {f}", sp)
    return out


def optimize(e, X=None, dry=False):
    """Build the challenger for one confirmed entry. Returns a record (and appends the challenger unless dry)."""
    import strategy_lab as S, prop_search as PS, prop_sim, test_engine as TE, review_prop as RP
    if X is None: _, X = TE.frame()
    spec = e["spec"]; (a0, a1), (b0, b1) = windows(e)
    M = S.data(spec.get("market"))["M"]
    idxA = np.where((M.session >= a0) & (M.session <= a1))[0]; idxB = np.where((M.session >= b0) & (M.session <= b1))[0]
    def es(sp, idx, seed=0):
        T = S.backtest(sp, X, idx); return PS.edge_stats(T.R.values, seed=seed) if len(T) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan}, T
    base_A, TA0 = es(spec, idxA); base_B, _ = es(spec, idxB, 1)
    rows = []
    for lbl, sp in refinements(spec):
        a, _ = es(sp, idxA)
        if a["n"] < max(60, 0.5 * base_A["n"]) or not np.isfinite(a["edge_lb10"]): continue
        rows.append({"change": lbl, "spec": sp, "n_A": a["n"], "lb10_A": a["edge_lb10"], "edge_A": a["edge"]})
    rows.sort(key=lambda r: -r["lb10_A"])
    best = None
    for r in rows[:5]:                                          # best few on the search years, then non-inferiority on validation
        if r["lb10_A"] < base_A["edge_lb10"] + MARGIN: break
        b, _ = es(r["spec"], idxB, 1)
        se = 1.0 / np.sqrt(max(b["n"], 1))
        if np.isfinite(b["edge"]) and b["edge"] > 0 and b["edge"] >= base_B["edge"] - 0.5 * se:
            best = dict(r, n_B=b["n"], edge_B=b["edge"]); break
    chosen = best["spec"] if best else spec
    # account playbook on the search years (prop EV with bootstrap 20th percentile > 0)
    TA = S.backtest(chosen, X, idxA); pb = None
    if len(TA) >= 30:
        cands = []
        for sz in PS.SIZINGS + PS.PLAYBOOKS:
            sp = dict(chosen, prop=sz); r = S.prop_score(TA, M, sp)[0]
            pts, w, st = S._prop_inputs(TA, M); bs = prop_sim.bootstrap(pts, w, r["plan"], S._sizer(sp, st), paths=300)
            if bs and bs["ev_p20"] > 0 and r["ev_per_eval"] > 0: cands.append((r["ev_per_eval"], sz, r["plan"], bs))
        if cands:
            ev, sz, plan, bs = max(cands, key=lambda c: c[0]); pb = {"prop": sz, "plan": plan, "ev_A": ev, "bootstrap_A": bs}
    if not best and not pb:
        rec = {"champion": e["name"], "status": "no improvement", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "base_A": base_A, "tried": len(rows)}
        return rec
    ch = dict(chosen); ch["name"] = f"refined: {e['name'][:60]}" + (f" ({best['change']})" if best else " (sizing)")
    if pb: ch["prop"] = pb["prop"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rec = {"champion": e["name"], "champion_key": RP.review_key(e), "challenger_key": S.spec_id(ch), "challenger": ch["name"],
           "date": today, "status": "forward", "change": best["change"] if best else "sizing only",
           "search_years": f"{a0}..{a1}", "base_A": base_A, "base_B": base_B,
           "refined": {k: v for k, v in (best or {}).items() if k != "spec"}, "playbook": pb, "tried": len(rows)}
    if not dry:
        entry = {"date": today, "name": ch["name"], "spec": ch, "source": "optimizer", "champion": e["name"],
                 "verdict": f"CHALLENGER (refinement of '{e['name'][:60]}'): {rec['change']}; chosen on {a0[:4]}-{a1[:4]} only; "
                            f"forward-tested next to the champion, promoted only if the coming weeks prove it better",
                 "review": f"CHALLENGER (auto, {today})"}
        with open(S.LOG, "a") as f: f.write(json.dumps(entry, default=float) + "\n")
    return rec


def run_new(X=None):
    """Create a challenger for every CONFIRMED champion that has none yet."""
    import strategy_lab as S, review_prop as RP
    O = _load(); RV = RP.load_reviews(); made = []
    for e0 in [json.loads(l) for l in open(S.LOG) if l.strip()]:
        e = RP.effective(e0, RV)
        if not str(e.get("review", "")).startswith("CONFIRMED") or "entry" not in e.get("spec", {}): continue
        k = RP.review_key(e)
        if k in O: continue
        rec = optimize(e, X); O[k] = rec; made.append(rec)
    json.dump(O, open(OPT, "w"), indent=1, default=float)
    return made


def judge(F):
    """Every evening: compare challenger vs champion on the forward trades (Bayesian, per-trade R)."""
    import review_prop as RP, strategy_lab as S
    O = _load(); news = []
    for k, rec in O.items():
        if rec.get("status") != "forward": continue
        fc = F[(F.id == rec["challenger_key"]) & F.traded] if len(F) else F
        fh = F[(F.id == rec["champion_key"]) & F.traded] if len(F) else F
        n = min(len(fc), len(fh))
        if n < 20: continue
        d = fc.R.mean() - fh.R.mean(); s2 = fc.R.var(ddof=1) / len(fc) + fh.R.var(ddof=1) / len(fh)
        from statistics import NormalDist
        prec = 1 / 0.05 ** 2 + 1 / max(s2, 1e-6); mu = (d / max(s2, 1e-6)) / prec
        p = 1 - NormalDist(mu, prec ** -0.5).cdf(0.0)
        rec.update(fwd_n=n, fwd_diff=round(float(d), 3), p_better=round(p, 3))
        if n >= MIN_FWD and p > 0.9:
            rec["status"] = "promoted"; news.append(f"🔧 Refinement promoted: {rec['challenger']} beats its champion on {n} forward trades "
                                                    f"(+{d:.3f}R per trade, P(better) {p:.0%})")
            E = [json.loads(l) for l in open(S.LOG) if l.strip()]
            for e in E:
                if RP.review_key(e) == rec["challenger_key"]: RP.save_review(e, review=f"CONFIRMED (promoted refinement, {datetime.now(timezone.utc):%Y-%m-%d}): better than its champion on {n} forward trades")
                if RP.review_key(e) == rec["champion_key"]: RP.save_review(e, review=f"SUPERSEDED (by its refinement, {datetime.now(timezone.utc):%Y-%m-%d})")
        elif (n >= 20 and p < 0.1) or n >= MAX_FWD:
            rec["status"] = "dropped"; news.append(f"Refinement dropped: {rec['challenger']} was not better on {n} forward trades (P(better) {p:.0%})")
    json.dump(O, open(OPT, "w"), indent=1, default=float)
    return news


if __name__ == "__main__":                                     # dry run on any entry name given, else on all CONFIRMED
    import strategy_lab as S, review_prop as RP
    name = sys.argv[1] if len(sys.argv) > 1 else None
    for e0 in [json.loads(l) for l in open(S.LOG) if l.strip()]:
        e = RP.effective(e0)
        if (name and name in e["name"]) and "entry" in e.get("spec", {}):
            print(json.dumps(optimize(e, dry=True), default=float, indent=1)[:3000]); break
