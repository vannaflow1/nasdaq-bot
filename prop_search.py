"""prop_search.py - Volta's nightly systematic search for a prop-firm strategy (runs on GitHub, ~2 hours a night).

Instead of waiting for ideas, Volta walks through a big grid of complete intraday NQ strategies
(entry type x direction rule x filter x stop x target) and sizing rules, and scores each one on what matters for the
mission: expected payouts per evaluation minus the fee, under every prop plan in knowledge/prop_firms.json.

Anti-self-deception protocol (thousands of tries WILL produce lucky winners):
  stage A  SEARCH      trades and account starts 2014-2021 only. Keep: >= 150 trades and EV after fee > 0.
  stage B  VALIDATION  the same strategy+plan+sizing on 2022-2023 only (never used to choose). Keep: EV > 0.
  stage C  EXAM        survivors go through the full strategy-lab protocol (both halves of 2014-2023, beats random
                       entries, survives double costs) and the LOCKED 2024-2026 exam (max 2 exams per night, 10 per week).
Every night ~70% of the budget explores new grid points, ~30% mutates the best validated candidates (local search).
Outputs: knowledge/prop_search/results.csv (everything), leaderboard in status.json ("prop_search"), a Discord note."""
import itertools, json, os, random, sys, time, warnings
from datetime import datetime, timezone
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
SHARD, SHARDS = int(os.environ.get("SHARD", "0")), int(os.environ.get("SHARDS", "1"))   # parallel GitHub jobs split the grid
OUT = os.path.join(K, "prop_search"); RES = os.path.join(OUT, f"results_{SHARD}.csv"); STATE = os.path.join(OUT, f"state_{SHARD}.json")
STATUS = os.path.join(HERE, "status.json")
BUDGET_MIN = float(os.environ.get("SEARCH_MINUTES", "120"))
SEARCH_END, VAL_END = "2021-12-31", "2023-12-31"

TIMES = ["08:31", "08:45", "09:00", "09:30", "10:00", "10:30", "11:30", "13:00", "13:30"]
SIDES = {"long": "long", "short": "short", "with overnight": "sign(k_on_return)", "against overnight": "0 - sign(k_on_return)",
         "with gap": "sign(k_gap)", "fade gap": "0 - sign(k_gap)", "with yesterday": "sign(p_return)", "against yesterday": "0 - sign(p_return)",
         "with 20d trend": "sign(r20)", "against 20d trend": "0 - sign(r20)", "with the open's side of the overnight range": "sign(k_on_pos - 0.5)"}
FILTERS = {"every day": "", "tail-day risk high": "pw_tail_day - 0.15", "tail-day risk low": "0.08 - pw_tail_day",
           "low dealer gamma": "0.3 - gex_rank", "high dealer gamma": "gex_rank - 0.7", "small overnight": "1 - k_on_vs_normal",
           "big overnight": "k_on_vs_normal - 1.3", "trending regime (Hurst>0.55)": "k_hurst - 0.55", "mean-reverting (Hurst<0.5)": "0.5 - k_hurst",
           "calm VIX (below 60d avg)": "mean(vix, 60) - vix", "gap fill likely": "pw_gap_fill - 0.65", "VIX curve inverted": "vix_curve - 1",
           "not Monday": "k_dow - 0.5", "Fri": "where(k_dow == 4, 1, 0)"}
LEVEL_SETS = [("yday_high", "yday_low"), ("on_high", "on_low"), ("asia_high", "asia_low"), ("london_high", "london_low"),
              ("or15_high", "or15_low"), ("vwap_up1", "vwap_dn1"), ("vwap_up2", "vwap_dn2"), ("r1", "s1"), ("exp50_up", "exp50_dn"),
              ("exp70_up", "exp70_dn"), ("atr10_up", "atr10_dn"), ("ewma1_up", "ewma1_dn")]
WINDOWS = [["08:30", "10:00"], ["08:45", "11:30"], ["10:00", "14:00"]]
STOPS = [{"points": 10}, {"points": 20}, {"points": 35}, {"points": 60}, {"range": 0.1}, {"range": 0.2}, {"range": 0.35}]
TARGETS = [{"R": 0.5}, {"R": 1}, {"R": 1.5}, {"R": 2}, {"R": 3}]
EXITS = ["14:55", "11:30"]
SIZINGS = [{"risk": 0.12, "eval_risk": 0.2}, {"risk": 0.2, "eval_risk": 0.35}, {"risk": 0.3, "eval_risk": 0.5}]


def grid():
    """Every grid point as a spec (deterministic order, shuffled with a fixed seed)."""
    G = []
    for t, (sn, sd), (fn, fl), st, tg, ex in itertools.product(TIMES, SIDES.items(), FILTERS.items(), STOPS, TARGETS, EXITS):
        if ex == "11:30" and t >= "10:30": continue
        G.append({"kind": "strategy", "name": f"{sn} at {t}, {fn}", "entry": {"type": "time", "at": t, "side": sd},
                  **({"filter": fl} if fl else {}), "stop": st, "target": tg, "exit": ex})
    for (up, dn), act, w, (fn, fl), st, tg in itertools.product(LEVEL_SETS, ("fade", "break"), WINDOWS, FILTERS.items(), STOPS, TARGETS):
        if up.startswith("or15") and w[0] < "08:45": continue
        for lv in (up, dn):
            G.append({"kind": "strategy", "name": f"{act} {lv} {w[0]}-{w[1]}, {fn}", "entry": {"type": "level", "level": lv, "action": act, "window": w},
                      **({"filter": fl} if fl else {}), "stop": st, "target": tg, "exit": "14:55"})
    random.Random(2026).shuffle(G)
    return G


def mutate(spec, rng):
    s = json.loads(json.dumps(spec)); k = rng.choice(["stop", "target", "filter", "time", "exit", "window"])
    if k == "stop": s["stop"] = rng.choice(STOPS)
    elif k == "target": s["target"] = rng.choice(TARGETS)
    elif k == "filter":
        fn, fl = rng.choice(list(FILTERS.items())); s.pop("filter", None)
        if fl: s["filter"] = fl
        s["name"] = s["name"].split(", ")[0] + ", " + fn
    elif k == "time" and s["entry"]["type"] == "time": s["entry"]["at"] = rng.choice(TIMES)
    elif k == "exit" and s["entry"]["type"] == "time" and s["entry"]["at"] < "10:30": s["exit"] = rng.choice(EXITS)
    elif k == "window" and s["entry"]["type"] == "level": s["entry"]["window"] = rng.choice(WINDOWS)
    s["name"] = "mutant: " + s["name"].replace("mutant: ", "")
    return s


def score(spec, X, D, S, P, idx, plan=None, sizings=SIZINGS):
    """Backtest on the sessions idx, then the prop simulator for each sizing (all plans, or one). Returns rows."""
    T = S.backtest(spec, X, idx)
    if len(T) < 30: return [], T
    m = S.metrics(T); rows = []
    for sz in sizings:
        sp = dict(spec, prop=sz)
        res = S.prop_score(T, D["M"], sp, plan) if plan else S.prop_score(T, D["M"], sp)
        for r in res[:1]:
            rows.append({"n": m["n"], "win": m["win"], "avg_R": m["avg_R"], "years_pos": m["years_pos"], "plan": r["plan"],
                         "risk": sz["risk"], "eval_risk": sz["eval_risk"], "pass": r["pass_rate"], "paid": r["avg_payout_per_eval"],
                         "ev": r["ev_per_eval"], "fee": r["fee"]})
    return rows, T


def main():
    import test_engine as TE, strategy_lab as S, prop_sim
    prop_sim.best_plan.__defaults__ = (None, 8)               # search stage: every 8th start day (2x faster, same ranking)
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time(); rng = random.Random(int(t0))
    M_, X = TE.frame(); D = S.data(); ses = D["M"].session.values
    idxA = np.where(ses <= SEARCH_END)[0]; idxB = np.where((ses > SEARCH_END) & (ses <= VAL_END))[0]
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"pos": 0, "nights": 0}
    R = pd.read_csv(RES) if os.path.exists(RES) else pd.DataFrame()
    ALL = all_results()
    done = set(ALL.spec_id) if len(ALL) else set()
    G = [g for j, g in enumerate(grid()) if j % SHARDS == SHARD]; tried = validated = 0; new_rows = []
    while time.time() - t0 < BUDGET_MIN * 60:
        if rng.random() < 0.3 and len(ALL) and (ALL.get("ev_val", pd.Series(dtype=float)) > 0).any():
            top = ALL[ALL.ev_val > 0].sort_values("ev_val", ascending=False).head(20)
            spec = mutate(json.loads(top.sample(1, random_state=rng.randint(0, 10**6)).spec.iloc[0]), rng)
        else:
            if st["pos"] >= len(G): st["pos"] = 0
            spec = G[st["pos"]]; st["pos"] += 1
        try:
            S.validate(spec); sid = S.spec_id(spec)
        except Exception:
            continue
        if sid in done: continue
        done.add(sid); tried += 1
        try:
            rows, T = score(spec, X, D, S, None, idxA)
        except Exception as e:
            print("skip", spec["name"], type(e).__name__, e); continue
        best = max(rows, key=lambda r: r["ev"]) if rows else None
        row = {"date": datetime.now(timezone.utc).date().isoformat(), "spec_id": sid, "name": spec["name"], "spec": json.dumps(spec)}
        if best: row.update({k: best[k] for k in ("n", "win", "avg_R", "years_pos", "plan", "risk", "eval_risk", "pass", "paid", "ev", "fee")})
        if best and best["n"] >= 150 and best["ev"] > 0:          # stage B: validation on 2022-2023, never used to choose
            sz = {"risk": best["risk"], "eval_risk": best["eval_risk"]}
            vr, _ = score(spec, X, D, S, None, idxB, plan=best["plan"], sizings=[sz])
            if vr:
                row.update({"n_val": vr[0]["n"], "pass_val": vr[0]["pass"], "paid_val": vr[0]["paid"], "ev_val": vr[0]["ev"]})
                validated += 1
        new_rows.append(row)
        if len(new_rows) % 25 == 0:
            print(f"{tried} tried, {validated} validated, {(time.time() - t0) / 60:.0f} min"); sys.stdout.flush()
    R = pd.concat([R, pd.DataFrame(new_rows)], ignore_index=True)
    # stage C: the best validated candidates take the full protocol + locked exam (max 2 per night)
    exams = []
    if "ev_val" in R and SHARD == 0:                          # job 1 only: max 2 exams per run (weekly exam cap still applies)
        cand = R[(R.ev_val > 0) & (R.get("exam", pd.Series(index=R.index, dtype=object)).isna())].sort_values("ev_val", ascending=False).head(2)
        for i, c in cand.iterrows():
            spec = json.loads(c.spec); spec["prop"] = {"risk": c.risk, "eval_risk": c.eval_risk}
            try:
                verdict, _ = S.evaluate(spec, X, source="prop-search")
            except Exception as e:
                verdict = f"error {type(e).__name__}"
            R.loc[i, "exam"] = verdict[:300]; exams.append((c["name"], verdict))
    R.to_csv(RES, index=False)
    st["nights"] += 1; json.dump(st, open(STATE, "w"))
    write_status(all_results(), len(grid()), st, tried, validated, exams)


def all_results():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "results_*.csv"))) + ([os.path.join(OUT, "results.csv")] if os.path.exists(os.path.join(OUT, "results.csv")) else [])
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def write_status(R, gsize, st, tried, validated, exams):
    tot = len(R); a = R[(R.get("ev", 0) > 0) & (R.get("n", 0) >= 150)] if tot else R
    v = R[R.get("ev_val", pd.Series(dtype=float)) > 0] if "ev_val" in R else R.iloc[0:0]
    lines = [f"PROP STRATEGY SEARCH - run {st['nights']} (job {SHARD + 1}/{SHARDS}): {tried} new strategies this run, {tot:,} tested in total "
             f"(grid {gsize:,} + mutations, {tot / gsize:.1%} covered)",
             f"Stage A (2014-21, EV after fee > 0): {len(a)} | Stage B (still positive on unseen 2022-23): {len(v)} | "
             f"exams taken: {int(R['exam'].notna().sum()) if 'exam' in R else 0}"]
    if len(v):
        lines += ["", "LEADERBOARD (ranked by EV per eval on unseen 2022-23):"]
        for _, r in v.sort_values("ev_val", ascending=False).head(6).iterrows():
            lines.append(f"- {r['name'][:70]} | {r.plan} risk {r.risk:.0%}/{r.eval_risk:.0%} | 2014-21 EV {r.ev:+.0f} (pass {r['pass']:.0%}) "
                         f"| 2022-23 EV {r.ev_val:+.0f} (pass {r.pass_val:.0%}) | {int(r.n)} trades, {r.avg_R:+.2f}R")
    else:
        lines += ["", "No strategy has stayed positive on the unseen 2022-23 years yet."]
    for name, vd in exams:
        lines += ["", f"EXAM: {name[:70]} -> {vd[:260]}"]
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["prop_search"] = lines; json.dump(s, open(STATUS, "w"), indent=1)
    print("\n".join(lines))
    try:
        import test_engine as TE
        ann = json.load(open(TE.ANN)) if os.path.exists(TE.ANN) else []
        passed = [n for n, vd in exams if str(vd).startswith("PROMISING STRATEGY")]
        title = "🏁 Volta found a prop strategy that passed the locked exam" if passed else "🔎 Volta's prop search"
        if not passed and SHARD != 0: return                  # one routine note per run (job 1), always announce a pass
        ann.append({"title": title, "body": "\n".join(lines)[:1800]}); json.dump(ann, open(TE.ANN, "w"), indent=1)
    except Exception as e:
        print("announce skipped:", e)


if __name__ == "__main__":
    main()
