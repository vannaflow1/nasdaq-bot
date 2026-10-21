"""families.py - mechanism families (expert review, 21 Oct 2026, upgrade 2).

Instead of discovering thousands of single specs (where the luck bar rises as fast as the search), Volta tests a small
number of PRE-REGISTERED families. Each family = a one-sentence mechanism + a fixed grid of 20-50 variants, frozen in git
before its validation years are ever looked at. One family statistic decides:
    the MEDIAN validation edge (mean net R per trade on 2022-23) across ALL variants,
compared with a placebo family on the same days (each variant's trades re-entered at a random minute / with a coin-flip
side, 100 draws). A real mechanism shows up as a plateau (most variants pay); luck shows up as a spike (one variant).
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
        out.append({"params": dict(zip(keys, c)), "sleeve": sleeve})
    return out


def fam_hash(fam):
    import hashlib
    return hashlib.sha1(json.dumps({"sleeve": fam["sleeve"], "grid": fam["grid"]}, sort_keys=True).encode()).hexdigest()[:12]


def trades(S, X, sleeve, lo, hi):
    """All trades of a sleeve between dates lo..hi (sessions), with the market for each."""
    rows = []
    for sp in sleeve:
        M = S.data(sp.get("market"))["M"]; idx = np.where((M.session >= lo) & (M.session <= hi))[0]
        T = S.backtest(sp, X, idx)
        if len(T): rows.append(T.assign(market=sp.get("market", "NQ"), spec=json.dumps(sp)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["session", "i", "pnl", "R", "side", "k", "market", "spec"])


def placebo_mean(S, T, rng, j):
    """Mean R of a no-edge twin of trades T: even j = same side at a random minute, odd j = same minute, coin-flip side."""
    Rs = []
    for spec_s, g in T.groupby("spec"):
        sp = json.loads(spec_s); D = S.data(sp.get("market")); e = sp["entry"]
        lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
        hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(sp.get("exit", "14:55")) - 5, 380)
        lo, hi = max(lo, 1), max(hi, lo + 2)
        for i, sd, k in zip(g.i.values, g.side.values, g.k.values):
            ov = (int(rng.integers(lo, hi)), int(sd)) if j % 2 == 0 else (int(k), int(rng.choice([-1, 1])))
            r = S.simulate_session(D, int(i), sp, entry_override=ov)
            if r: Rs.append(r[1])
    return float(np.mean(Rs)) if len(Rs) >= 20 else np.nan


def ledger():
    return pd.read_csv(LEDGER) if os.path.exists(LEDGER) else pd.DataFrame()


def score_family(fam, X, S, reps=100, seed=7):
    import prop_search as PS
    V = variants(fam); rng = np.random.default_rng(seed); rows = []
    TB_all = []
    for v in V:
        TA = trades(S, X, v["sleeve"], "1900-01-01", A_END); TB = trades(S, X, v["sleeve"], "2022-01-01", B_END)
        ea = PS.edge_stats(TA.R.values) if len(TA) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan, "edge_t": np.nan}
        eb = PS.edge_stats(TB.R.values, seed=1) if len(TB) else {"n": 0, "edge": np.nan, "edge_lb10": np.nan, "edge_t": np.nan}
        rows.append({"params": json.dumps(v["params"]), "n_A": ea["n"], "edge_A": ea["edge"], "lb10_A": ea["edge_lb10"],
                     "n_B": eb["n"], "edge_B": eb["edge"], "lb10_B": eb["edge_lb10"]})
        TB_all.append(TB)
    R = pd.DataFrame(rows); ok = R[R.n_B >= 20]
    if len(ok) < 5:
        return {"verdict": "TOO FEW TRADES", "variants": len(V), "usable": len(ok)}, R, V
    med_B = float(ok.edge_B.median()); share_pos = float((ok.edge_B > 0).mean()); med_A = float(R[R.n_A >= 20].edge_A.median())
    pl = []                                                  # placebo family: median over variants of placebo means
    for j in range(reps):
        m = [placebo_mean(S, TB_all[i], rng, j) for i in ok.index]
        m = [x for x in m if np.isfinite(x)]
        if m: pl.append(float(np.median(m)))
    pl = np.array(pl); p = float((pl >= med_B).mean()) if len(pl) else 1.0
    L = ledger(); k = (len(L) + 1)
    alpha = ALPHA / k
    passed = med_B > 0 and share_pos >= 0.6 and p < alpha
    res = {"variants": len(V), "usable": len(ok), "median_edge_A": round(med_A, 4), "median_edge_B": round(med_B, 4),
           "share_positive_B": round(share_pos, 3), "placebo_median_mean": round(float(pl.mean()), 4) if len(pl) else None,
           "p": round(p, 4), "families_scored": k, "alpha": round(alpha, 5), "passed": bool(passed)}
    return res, R, V


def exam_family(fam, R, V, X, S):
    """Best variant chosen on the SEARCH years only (bootstrap lower bound), then the locked exam on 2024-now."""
    import prop_search as PS, prop_sim
    best_i = int(R.lb10_A.fillna(-9).idxmax()); v = V[best_i]
    ex = json.load(open(S.EXAMS)) if os.path.exists(S.EXAMS) else {}
    w = S._week()
    if ex.get(w, 0) >= S.EXAMS_PER_WEEK:
        return v, "PASSED THE FAMILY TEST, WAITING FOR EXAM (weekly exam budget used up)", {}
    ex[w] = ex.get(w, 0) + 1; json.dump(ex, open(S.EXAMS, "w"), indent=1)
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
    return v, (f"PROMISING STRATEGY (family {fam['id']}, passed the locked exam): edge on 2024-now {ee['edge']:+.3f}R "
               f"(90% lower bound {ee['edge_lb10']:+.3f}R, {ee['n']} trades); priced on {pr['plan']}: pass {pr['pass_rate']:.0%}, "
               f"EV {pr['ev_per_eval']:+.0f}$/eval"), det


def main():
    import strategy_lab as S, test_engine as TE
    only = sys.argv[sys.argv.index("--id") + 1] if "--id" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 100
    F = json.load(open(REG)) if os.path.exists(REG) else []
    _, X = TE.frame(); out_lines = []
    for fam in F:
        if fam.get("status") != "registered" or (only and fam["id"] != only): continue
        if not fam.get("frozen") or fam.get("hash") != fam_hash(fam):
            print(fam["id"], "not frozen or changed after registration - skipped"); continue
        t0 = time.time()
        res, R, V = score_family(fam, X, S, reps=reps)
        verdict, det = res.get("verdict", "PASSED" if res.get("passed") else "FAILED"), {}
        if res.get("passed"):
            v, verdict, det = exam_family(fam, R, V, X, S)
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
        fam["status"] = "scored"; fam["scored"] = row["date"]
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
