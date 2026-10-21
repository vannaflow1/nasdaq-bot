"""prop_search.py - Volta's nightly systematic search for a prop-firm strategy (runs on GitHub, ~2 hours a night).

Instead of waiting for ideas, Volta walks through a big grid of complete intraday NQ strategies
(entry type x direction rule x filter x stop x target) and sizing rules, and scores each one on what matters for the
mission: expected payouts per evaluation minus the fee, under every prop plan in knowledge/prop_firms.json.

Anti-self-deception protocol (thousands of tries WILL produce lucky winners):
  stage A  SEARCH      trades and account starts 2014-2021 only. Keep: >= 150 trades and EV after fee > 0.
  stage B  VALIDATION  the same strategy+plan+sizing on 2022-2023 only (never used to choose). Keep: EV > 0.
  LUCK BAR             with thousands of validated tries, the best 2022-23 EV is inflated by luck. Every validated
                       candidate also gets 2 no-edge placebos scored on its 2022-23 days with the same stop, target, plan
                       and sizing: one entered at a random minute (same side), one at the same minute with a coin-flip side. Per market, the luck bar is the EV that the best of
                       K no-edge strategies reaches with 95% probability, K = that market's number of validated candidates.
                       Only candidates above the bar "beat luck": they rank the leaderboard, steer the market focus, are
                       mutated first and are the only ones sent to the locked exam (once the bar exists).
  stage C  EXAM        survivors of all jobs go through the full strategy-lab protocol (both halves of 2014-2023, beats random
                       entries, survives double costs) and the LOCKED 2024-2026 exam (max 2 exams per night, 10 per week).
  PORTFOLIO            job 1 then combines 2-4 low-correlation stage-A strategies into ONE account (chosen on 2014-21
                       only, validated on 2022-23 + the 5-account farm) -> knowledge/prop_search/portfolios.csv.
Every night ~70% of the budget explores new grid points, ~30% mutates the best validated candidates (local search).
Outputs: knowledge/prop_search/results.csv (everything), leaderboard in status.json ("prop_search"), a Discord note."""
import itertools, json, os, random, sys, time, warnings
from datetime import datetime, timezone
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
SHARD, SHARDS = int(os.environ.get("SHARD", "0")), int(os.environ.get("SHARDS", "1"))   # parallel GitHub jobs split the grid
# TRACK "classic": search 2014-21, validate 2022-23, locked exam 2024-26 (long history guards against luck).
# TRACK "recent" (owner, 21 Oct 2026: an edge may only exist since 2024): search 2024-01..2025-03, validate 2025-04..today,
#   a STRICTER luck bar (99%) because the short window gives far fewer independent accounts, then the recent review
#   (review_prop.review_recent) and finally the coming weeks of new market data (forward test) as the real exam.
TRACK = os.environ.get("TRACK", "classic")
OUT = os.path.join(K, "prop_search") if TRACK == "classic" else os.path.join(K, "prop_search", "recent")
RES = os.path.join(OUT, f"results_{SHARD}.csv"); STATE = os.path.join(OUT, f"state_{SHARD}.json")
STATUS = os.path.join(HERE, "status.json")
BUDGET_MIN = float(os.environ.get("SEARCH_MINUTES", "120"))
SEARCH_START, SEARCH_END, VAL_END = ("1900-01-01", "2021-12-31", "2023-12-31") if TRACK == "classic" else ("2024-01-01", "2025-03-31", "2099-12-31")
MIN_TRADES = 150 if TRACK == "classic" else 60
LUCK_CONF = 0.95 if TRACK == "classic" else 0.99
STATUS_KEY = "prop_search" if TRACK == "classic" else "prop_search_recent"
SEARCH_MARKETS = [m.strip() for m in os.environ.get("SEARCH_MARKETS", "NQ").split(",") if m.strip()]
LBL_A, LBL_B = ("2014-21", "2022-23") if TRACK == "classic" else ("2024-01..2025-03", "2025-04..now")
SIM_VERSION = "harsh-1"      # rows without it were scored before the harsher fills / own-stop worst point / daily loss limit

TIMES = ["08:31", "08:45", "09:00", "09:30", "10:00", "10:30", "11:30", "13:00", "13:30"]
SIDES = {"long": "long", "short": "short", "with overnight": "sign(k_on_return)", "against overnight": "0 - sign(k_on_return)",
         "with gap": "sign(k_gap)", "fade gap": "0 - sign(k_gap)", "with yesterday": "sign(p_return)", "against yesterday": "0 - sign(p_return)",
         "with 20d trend": "sign(r20)", "against 20d trend": "0 - sign(r20)", "with the open's side of the overnight range": "sign(k_on_pos - 0.5)"}
FILTERS = {"every day": "", "tail-day risk high": "pw_tail_day - 0.15", "tail-day risk low": "0.08 - pw_tail_day",
           "low dealer gamma": "0.3 - gex_rank", "high dealer gamma": "gex_rank - 0.7", "small overnight": "1 - k_on_vs_normal",
           "big overnight": "k_on_vs_normal - 1.3", "trending regime (Hurst>0.55)": "k_hurst - 0.55", "mean-reverting (Hurst<0.5)": "0.5 - k_hurst",
           "calm VIX (below 60d avg)": "mean(vix, 60) - vix", "gap fill likely": "pw_gap_fill - 0.65", "VIX curve inverted": "vix_curve - 1",
           "not Monday": "k_dow - 0.5", "Fri": "where(k_dow > 3.5, 1, 0)",
           "no red-folder news": "0.5 - k_red_any", "red-folder news day": "k_red_any - 0.5", "no FOMC": "0.5 - k_fomc_day",
           "volatile VIX (above 60d avg)": "vix - mean(vix, 60)", "big expected range (top third)": "rank(iv30, 252) - 0.67",
           "small expected range (bottom third)": "0.33 - rank(iv30, 252)"}
LEVEL_SETS = [("yday_high", "yday_low"), ("on_high", "on_low"), ("asia_high", "asia_low"), ("london_high", "london_low"),
              ("or15_high", "or15_low"), ("vwap_up1", "vwap_dn1"), ("vwap_up2", "vwap_dn2"), ("r1", "s1"), ("exp50_up", "exp50_dn"),
              ("exp70_up", "exp70_dn"), ("atr10_up", "atr10_dn"), ("ewma1_up", "ewma1_dn")]
WINDOWS = [["08:30", "10:00"], ["08:45", "11:30"], ["10:00", "14:00"]]
STOPS = [{"points": 10}, {"points": 20}, {"points": 35}, {"points": 60}, {"range": 0.1}, {"range": 0.2}, {"range": 0.35}]
TARGETS = [{"R": 0.5}, {"R": 1}, {"R": 1.5}, {"R": 2}, {"R": 3}]
EXITS = ["14:55", "11:30"]
SIZINGS = [{"risk": 0.12, "eval_risk": 0.2}, {"risk": 0.2, "eval_risk": 0.35}, {"risk": 0.3, "eval_risk": 0.5}]
# account playbooks (how to run the account, not the strategy): tried on the SEARCH years only, for candidates whose
# best base sizing is positive or a near-miss (EV > -half the fee); the best one is then validated like everything else.
PLAYBOOKS = [{"risk": 0.2, "eval_risk": 0.5, "eval_finish": True}, {"risk": 0.12, "eval_risk": 0.35, "eval_finish": True},
             {"risk": 0.3, "eval_risk": 0.7, "eval_finish": True}, {"risk": 0.2, "eval_risk": 0.2, "eval_finish": True},
             {"risk": 0.08, "eval_risk": 0.35}, {"risk": 0.2, "eval_risk": 0.5, "eval_finish": True, "funded_micros": 2},
             {"risk": 0.2, "eval_risk": 0.7, "eval_finish": True, "funded_micros": 3}]
# trade management (how each trade is run): every grid strategy also exists with these
MANAGES = [None, {"be_at_R": 0.5}, {"be_at_R": 1.0}, {"trail_R": 1.0}, {"partial": {"at_R": 1.0, "frac": 0.5}}]
MANAGE_NAMES = {None: "", "be_at_R": "breakeven at {}R", "trail_R": "trail {}R", "partial": "half off at {}R"}


def _mg_name(mg):
    if not mg: return ""
    k = next(iter(mg)); v = mg[k]["at_R"] if k == "partial" else mg[k]
    return ", " + MANAGE_NAMES[k].format(v)


MARKETS = ["NQ", "GC", "CL"]          # Nasdaq, gold, crude oil (micros: MNQ / MGC / MCL)
OWN_SIDES = {"long": "long", "short": "short", "with its gap": "own:gap", "fade its gap": "own:-gap",
             "with its move since midnight": "own:mid", "against its move since midnight": "own:-mid",
             "with its overnight-range side": "own:pos", "against its overnight-range side": "own:-pos"}
OTHER_FILTERS = ["every day", "calm VIX (below 60d avg)", "volatile VIX (above 60d avg)", "VIX curve inverted", "not Monday", "Fri",
                 "no red-folder news", "red-folder news day", "no FOMC"]


def grid():
    """Every grid point as a spec (deterministic order, shuffled with a fixed seed). Gold and oil use stops sized by
    their own expected range (point stops are NQ-sized) and skip the NQ-only power filters."""
    G = []
    for mk in MARKETS:
        stops = STOPS if mk == "NQ" else [x for x in STOPS if "range" in x]
        filters = FILTERS if mk == "NQ" else {k: v for k, v in FILTERS.items() if k in OTHER_FILTERS}
        sides = SIDES if mk == "NQ" else OWN_SIDES
        tag = "" if mk == "NQ" else f"[{mk}] "
        for t, (sn, sd), (fn, fl), st, tg, ex in itertools.product(TIMES, sides.items(), filters.items(), stops, TARGETS, EXITS):
            if ex == "11:30" and t >= "10:30": continue
            for mg in MANAGES:
                if mg and "R" in tg and ((mg.get("be_at_R") or mg.get("trail_R") or (mg.get("partial") or {}).get("at_R") or 0) >= tg["R"]): continue
                G.append({"kind": "strategy", "market": mk, "name": f"{tag}{sn} at {t}, {fn}{_mg_name(mg)}", "entry": {"type": "time", "at": t, "side": sd},
                          **({"filter": fl} if fl else {}), "stop": st, "target": tg, "exit": ex, **({"manage": mg} if mg else {})})
        for (up, dn), act, w, (fn, fl), st, tg in itertools.product(LEVEL_SETS, ("fade", "break"), WINDOWS, filters.items(), stops, TARGETS):
            if up.startswith("or15") and w[0] < "08:45": continue
            for lv in (up, dn):
                for mg in MANAGES:
                    if mg and "R" in tg and ((mg.get("be_at_R") or mg.get("trail_R") or (mg.get("partial") or {}).get("at_R") or 0) >= tg["R"]): continue
                    G.append({"kind": "strategy", "market": mk, "name": f"{tag}{act} {lv} {w[0]}-{w[1]}, {fn}{_mg_name(mg)}",
                              "entry": {"type": "level", "level": lv, "action": act, "window": w},
                              **({"filter": fl} if fl else {}), "stop": st, "target": tg, "exit": "14:55", **({"manage": mg} if mg else {})})
    random.Random(2026).shuffle(G)
    return G


def mutate(spec, rng):
    s = json.loads(json.dumps(spec)); k = rng.choice(["stop", "target", "filter", "time", "exit", "window", "manage"])
    if k == "manage":
        mg = rng.choice(MANAGES); s.pop("manage", None)
        if mg: s["manage"] = mg
    if k == "stop": s["stop"] = rng.choice(STOPS if (s.get("market") or "NQ") == "NQ" else [x for x in STOPS if "range" in x])
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


def edge_stats(R, B=1000, block=5, seed=0):
    """THE search metric since 21 Oct 2026 (expert review): the edge in the trade stream, not prop EV (prop EV rewards
    variance and aggressive sizing). Mean net R per trade, its t-stat, and the 10th percentile of the mean from a
    stationary block bootstrap (Politis-Romano, mean block 5 trades) = edge_lb10. A candidate needs edge_lb10 > 0."""
    R = np.asarray(R, float); R = R[np.isfinite(R)]; n = len(R)
    if n < 20: return {"n": n, "edge": float(R.mean()) if n else np.nan, "edge_t": np.nan, "edge_lb10": np.nan}
    rng = np.random.default_rng(seed); p = 1.0 / block
    new = rng.random((B, n)) < p; new[:, 0] = True
    pos = np.arange(n)[None, :].repeat(B, 0)
    bs = np.maximum.accumulate(np.where(new, pos, 0), axis=1)            # position where the current block started
    starts = rng.integers(0, n, (B, n))
    st = np.take_along_axis(starts, bs, axis=1)
    idx = (st + (pos - bs)) % n
    means = R[idx].mean(1)
    sd = R.std(ddof=1)
    return {"n": n, "edge": float(R.mean()), "edge_t": float(R.mean() / (sd / np.sqrt(n))) if sd > 0 else np.nan,
            "edge_lb10": float(np.percentile(means, 10))}


def placebo_edges(spec, T, S, rng, reps=4):
    """No-edge twins of a validated candidate on its own validation days (same stop/target/exit): even draws = same side at
    a random minute, odd draws = same minute with a coin-flip side. Returns their mean net R (the luck pool for the bar)."""
    D = S.data(spec.get("market")); e = spec["entry"]
    lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
    hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2); out = []
    for j in range(reps):
        Rs = []
        for i, sd, k in zip(T.i.values, T.side.values, T.k.values):
            ov = (rng.randint(lo, hi - 1), int(sd)) if j % 2 == 0 else (int(k), rng.choice((-1, 1)))
            r = S.simulate_session(D, int(i), spec, entry_override=ov)
            if r: Rs.append(r[1])
        if len(Rs) >= 30: out.append(float(np.mean(Rs)))
    return out


NULL = os.path.join(OUT, f"null_{SHARD}.csv")
NULL_PER_CANDIDATE, NULL_MIN = 2, 30                       # placebo draws per validated candidate; draws needed for a bar


def placebo_evs(spec, T, S, plan, sz, rng, reps=NULL_PER_CANDIDATE):
    """No-edge twins of a validated candidate on its own 2022-23 days, same stop/target/exit, plan and sizing. Even draws:
    same side, entered at a random minute (shuffled entry, as in strategy_lab.prop_path). Odd draws: same entry minute,
    coin-flip side (keeps the timing and holding time, removes any direction skill). Returns their EVs per eval."""
    D = S.data(spec.get("market")); M = D["M"]; e = spec["entry"]
    lo = S.mins(e["window"][0]) if e["type"] == "level" else 1
    hi = S.mins(e["window"][1]) if e["type"] == "level" else min(S.mins(spec.get("exit", "14:55")) - 5, 380)
    lo, hi = max(lo, 1), max(hi, lo + 2); out = []
    for j in range(reps):
        rows = []
        for s_, i, sd, k in zip(T.session.values, T.i.values, T.side.values, T.k.values):
            ov = (rng.randint(lo, hi - 1), int(sd)) if j % 2 == 0 else (int(k), rng.choice((-1, 1)))
            r = S.simulate_session(D, int(i), spec, entry_override=ov)
            if r: rows.append((s_, i, r[0], r[1], r[2], r[3]))
        P = pd.DataFrame(rows, columns=["session", "i", "pnl", "R", "side", "k"])
        out.append(S.prop_score(P, M, dict(spec, prop=sz), plan)[0]["ev_per_eval"] if len(P) >= 30 else None)
    return [x for x in out if x is not None]


def all_null():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "null_*.csv")))
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame(columns=["market", "ev"])


def luck_bar(null_ev, k, conf=None):
    """EV that the best of k no-edge strategies stays below with probability conf: the conf**(1/k) quantile of the
    placebo EVs (P(max of k <= x) = F(x)**k). Beyond the pool's own range, a normal tail fitted to the pool, never
    below the pool's max. None while the pool has fewer than NULL_MIN draws."""
    from statistics import NormalDist
    conf = LUCK_CONF if conf is None else conf
    x = np.sort(np.asarray(null_ev, dtype=float)); x = x[np.isfinite(x)]
    if len(x) < NULL_MIN or k < 1: return None
    q = conf ** (1.0 / k)
    if q <= (len(x) - 1) / len(x):
        return float(np.quantile(x, q))
    tail = float(x.mean() + x.std(ddof=1) * NormalDist().inv_cdf(q))
    return max(tail, float(x[-1]))


def market_of(A):
    return A.spec.map(lambda x: json.loads(x).get("market", "NQ") if isinstance(x, str) else "NQ") if len(A) and "spec" in A else pd.Series(dtype=object)


def luck(A=None, N=None):
    """Per market: trials (tested), validated candidates K, placebo draws, the luck bar, and each row's excess over it."""
    A = all_results() if A is None else A; N = all_null() if N is None else N
    out = {}; mk = market_of(A)
    for m in MARKETS:
        a = A[mk == m] if len(A) else A
        k = int(a["edge_val"].notna().sum()) if len(a) and "edge_val" in a else 0
        nv = N[N.market == m]["edge"].dropna().values if len(N) and "edge" in N else np.array([])
        bar = luck_bar(nv, k)
        beat = int((a["edge_val"] > bar).sum()) if bar is not None and k else 0
        out[m] = {"tested": int(len(a)), "validated": k, "null_draws": int(len(nv)),
                  "null_mean": round(float(np.mean(nv)), 3) if len(nv) else None,
                  "bar": round(bar, 3) if bar is not None else None, "beat_luck": beat}
    return out


def excess(A, L):
    """Validation edge (mean net R) minus the market's luck bar (NaN where no bar exists yet or the row was not validated)."""
    if not len(A) or "edge_val" not in A: return pd.Series(dtype=float)
    bars = market_of(A).map(lambda m: L.get(m, {}).get("bar"))
    return A.edge_val - pd.to_numeric(bars, errors="coerce")


def content_id(spec):
    """Identity of what a spec trades (its name excluded), so a mutation that changed nothing is not tested again."""
    import strategy_lab as S
    return S.spec_id({k: v for k, v in spec.items() if k not in ("name", "prop")})


def stage_idx(S, spec, stage):
    ses = S.data(spec.get("market"))["M"].session.values
    return np.where((ses >= SEARCH_START) & (ses <= SEARCH_END))[0] if stage == "A" else np.where((ses > SEARCH_END) & (ses <= VAL_END))[0]


def score(spec, X, D, S, P, idx, plan=None, sizings=SIZINGS):
    """Backtest on the sessions idx (or "A"/"B" = search/validation years of the spec's market), then the prop simulator
    for each sizing (all plans, or one). Returns rows."""
    if isinstance(idx, str): idx = stage_idx(S, spec, idx)
    D = S.data(spec.get("market"))
    T = S.backtest(spec, X, idx)
    if len(T) < 30: return [], T
    m = S.metrics(T); rows = []
    for sz in sizings:
        sp = dict(spec, prop=sz)
        res = S.prop_score(T, D["M"], sp, plan) if plan else S.prop_score(T, D["M"], sp)
        for r in res[:1]:
            rows.append({"n": m["n"], "win": m["win"], "avg_R": m["avg_R"], "years_pos": m["years_pos"], "plan": r["plan"],
                         "risk": sz["risk"], "eval_risk": sz["eval_risk"], "playbook": json.dumps(sz), "pass": r["pass_rate"], "paid": r["avg_payout_per_eval"],
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
    done_c = {content_id(json.loads(x)) for x in ALL.spec if isinstance(x, str)} if len(ALL) and "spec" in ALL else set()
    G_all = [g for j, g in enumerate(grid()) if j % SHARDS == SHARD]; tried = validated = 0; new_rows = []; null_rows = []
    GM = {mk: [g for g in G_all if g.get("market", "NQ") == mk] for mk in MARKETS}
    L0 = luck(ALL)                                             # luck bars per market (from the stored placebo draws)
    print("luck bars:", {m: v["bar"] for m, v in L0.items()})
    pref = preferences(ALL)                                    # Volta's market focus, learned from its own results
    st.setdefault("pos_m", {mk: 0 for mk in MARKETS})
    print("market focus:", pref["weights"], "|", pref["why"])
    G = G_all
    while time.time() - t0 < BUDGET_MIN * 60:
        if rng.random() < 0.3 and len(ALL) and "edge_val" in ALL and (ALL.edge_val > 0).any():
            xs = excess(ALL, L0)                                  # parents: beat the luck bar first, else best validation edge
            top = ALL.loc[xs[xs > 0].sort_values(ascending=False).index[:20]] if (xs > 0).any() else \
                ALL[ALL.edge_val > 0].sort_values("edge_val", ascending=False).head(20)
            spec = mutate(json.loads(top.sample(1, random_state=rng.randint(0, 10**6)).spec.iloc[0]), rng)
        else:
            mk = rng.choices(list(pref["weights"]), weights=list(pref["weights"].values()))[0]
            if mk not in SEARCH_MARKETS: mk = SEARCH_MARKETS[0]   # GC/CL only through families with a mechanism (review)
            Gm = GM[mk]
            if st["pos_m"].get(mk, 0) >= len(Gm): st["pos_m"][mk] = 0
            spec = Gm[st["pos_m"].get(mk, 0)]; st["pos_m"][mk] = st["pos_m"].get(mk, 0) + 1
        if (spec.get("market") or "NQ") not in SEARCH_MARKETS: continue
        try:
            S.validate(spec); sid = S.spec_id(spec)
        except Exception:
            continue
        cid = content_id(spec)
        if sid in done or cid in done_c: continue                # a mutant that only renamed its parent is not a new try
        done.add(sid); done_c.add(cid); tried += 1
        row = {"date": datetime.now(timezone.utc).date().isoformat(), "spec_id": sid, "name": spec["name"], "spec": json.dumps(spec),
               "sim": SIM_VERSION, "metric": "edge-v1"}
        try:                                                     # stage A: the EDGE on the search years (no prop sim yet)
            TA = S.backtest(spec, X, stage_idx(S, spec, "A"))
        except Exception as e:
            print("skip", spec["name"], type(e).__name__, e); continue
        ea = edge_stats(TA.R.values) if len(TA) else {"n": 0, "edge": np.nan, "edge_t": np.nan, "edge_lb10": np.nan}
        row.update({"n": ea["n"], "avg_R": round(ea["edge"], 4) if np.isfinite(ea["edge"]) else None,
                    "edge_t": round(ea["edge_t"], 2) if np.isfinite(ea["edge_t"]) else None,
                    "edge_lb10": round(ea["edge_lb10"], 4) if np.isfinite(ea["edge_lb10"]) else None})
        if ea["n"] >= MIN_TRADES and np.isfinite(ea["edge_lb10"]) and ea["edge_lb10"] > 0:
            try:                                                 # priced only now: the prop simulator on the base sizings
                rows, _ = score(spec, X, D, S, None, "A")
                best = max(rows, key=lambda r: r["ev"]) if rows else None
                if best: row.update({k: best[k] for k in ("win", "years_pos", "plan", "risk", "eval_risk", "playbook", "pass", "paid", "ev", "fee")})
            except Exception as e:
                best = None; print("pricing skipped:", type(e).__name__, e)
            TB = S.backtest(spec, X, stage_idx(S, spec, "B"))   # stage B: the edge on the validation years, never used to choose
            eb = edge_stats(TB.R.values, seed=1) if len(TB) else {"n": 0, "edge": np.nan, "edge_t": np.nan, "edge_lb10": np.nan}
            if eb["n"] >= 30:
                row.update({"n_val": eb["n"], "edge_val": round(eb["edge"], 4), "edge_t_val": round(eb["edge_t"], 2) if np.isfinite(eb["edge_t"]) else None,
                            "edge_lb10_val": round(eb["edge_lb10"], 4) if np.isfinite(eb["edge_lb10"]) else None})
                validated += 1
                try:                                              # luck control: no-edge twins on the same validation days
                    for e0 in placebo_edges(spec, TB, S, rng):
                        null_rows.append({"date": row["date"], "market": spec.get("market", "NQ"), "spec_id": sid, "edge": e0})
                except Exception as e:
                    print("placebo skipped:", type(e).__name__, e)
                if best and eb["edge_lb10"] > 0:                  # price the validated edge (information, not a gate)
                    try:
                        sz = json.loads(best["playbook"])
                        vr, _ = score(spec, X, D, S, None, "B", plan=best["plan"], sizings=[sz])
                        if vr: row.update({"pass_val": vr[0]["pass"], "paid_val": vr[0]["paid"], "ev_val": vr[0]["ev"]})
                    except Exception as e:
                        print("val pricing skipped:", e)
        new_rows.append(row)
        if len(new_rows) % 25 == 0:
            print(f"{tried} tried, {validated} validated, {(time.time() - t0) / 60:.0f} min"); sys.stdout.flush()
    R = pd.concat([R, pd.DataFrame(new_rows)], ignore_index=True)
    if null_rows:
        N0 = pd.read_csv(NULL) if os.path.exists(NULL) else pd.DataFrame()
        pd.concat([N0, pd.DataFrame(null_rows)], ignore_index=True).to_csv(NULL, index=False)
    L = luck(pd.concat([all_results().pipe(lambda a: a[~a.spec_id.isin(R.spec_id)] if len(a) else a), R], ignore_index=True))
    # stage C: the best validated candidates of ALL jobs take the full protocol + locked exam (job 1 only, max 2 per run;
    # the weekly exam cap still applies). Verdicts go to the exam ledger (exams.csv) so other jobs' files are never touched;
    # a candidate that was only told "WAITING FOR EXAM" (weekly budget used up) stays eligible for a later run.
    exams = []
    exb = json.load(open(S.EXAMS)) if os.path.exists(S.EXAMS) else {}
    budget_left = exb.get(S._week(), 0) < S.EXAMS_PER_WEEK
    if SHARD == 0 and not budget_left: print("weekly exam budget used up - candidates wait for next week")
    if SHARD == 0 and budget_left:
        A2 = pd.concat([all_results().pipe(lambda a: a[~a.spec_id.isin(R.spec_id)] if len(a) else a), R], ignore_index=True)
        if "edge_val" in A2:
            sat = exam_ledger()
            ex_col = A2.get("exam", pd.Series(index=A2.index, dtype=object)).astype(object)
            ex_col = ex_col.where(ex_col.notna(), A2.spec_id.map(sat))
            waiting = ex_col.fillna("").astype(str).str.contains("WAITING FOR EXAM")
            free = (A2.get("edge_lb10_val", pd.Series(index=A2.index, dtype=float)) > 0) & (ex_col.isna() | waiting)
            xs = excess(A2, L); has_bar = market_of(A2).map(lambda m: L[m]["bar"] is not None).astype(bool)
            free &= ~has_bar | (xs > 0)                       # where a luck bar exists, only candidates above it take the exam
            if TRACK != "classic": free &= has_bar              # new-regime track: no exam at all before its (99%) luck bar exists
            rk = xs.where(has_bar, A2.edge_val)[free].sort_values(ascending=False)
            for i, c in A2.loc[rk.index[:2]].iterrows():
                spec = json.loads(c.spec)
                if not isinstance(c.get("plan"), str): continue          # never priced (no positive edge on the search years)
                pbk = c.get("playbook") if hasattr(c, "get") else None
                spec["prop"] = json.loads(pbk) if isinstance(pbk, str) and pbk.startswith("{") else {"risk": c.risk, "eval_risk": c.eval_risk}
                try:
                    if TRACK == "classic":
                        verdict, _ = S.evaluate(spec, X, source="prop-search")
                    else:
                        import review_prop
                        verdict = review_prop.recent_exam(spec, X, c["name"], c.plan)
                except Exception as e:
                    verdict = f"error {type(e).__name__}"
                exams.append((c["name"], verdict))
                led = pd.read_csv(EXLOG) if os.path.exists(EXLOG) else pd.DataFrame()
                pd.concat([led, pd.DataFrame([{"date": datetime.now(timezone.utc).date().isoformat(), "spec_id": c.spec_id,
                                                "name": c["name"], "verdict": verdict[:300]}])], ignore_index=True).to_csv(EXLOG, index=False)
                if c.spec_id in set(R.spec_id): R.loc[R.spec_id == c.spec_id, "exam"] = verdict[:300]
    R.to_csv(RES, index=False)
    if SHARD == 0 and os.environ.get("PORTFOLIO_MINUTES", "10") != "0":   # portfolio stage (job 1 only)
        try:
            portfolio_stage(all_results(), X, S, minutes=float(os.environ.get("PORTFOLIO_MINUTES", "10")))
        except Exception as e:
            print("portfolio stage failed:", type(e).__name__, e)
    st["nights"] += 1; json.dump(st, open(STATE, "w"))
    pref = preferences(all_results(), save=(SHARD == 0))
    write_status(all_results(), len(grid()), st, tried, validated, exams, pref, luck())


# ------------------------------------------------------------------ portfolio stage: several weak edges in one account
PORT = os.path.join(OUT, "portfolios.csv")
PORT_POOL, PORT_MAX_CORR, PORT_SCREEN, PORT_VALIDATE = 16, 0.3, 30, 5


def _daily(spec, X, S, cal, worst=False):
    """A strategy's day-by-day result on the NQ calendar `cal` (sessions), in MNQ-equivalent points per 1 micro
    (with worst=True also the day's worst point: that trade's own stop or its actual loss, as strategy_lab._prop_inputs)."""
    D = S.data(spec.get("market")); M = D["M"]
    idx = np.where((M.session.values >= cal[0]) & (M.session.values <= cal[-1]))[0]
    T = S.backtest(spec, X, idx); pv = float(M.attrs.get("pv", 2.0))
    out = pd.Series(0.0, index=cal); wst = pd.Series(0.0, index=cal)
    if len(T):
        t = T[T.session.isin(cal)]; eq = t.pnl.values * pv / 2.0; out[t.session.values] = eq
        R = t.R.values; own = np.abs(eq / np.where(np.abs(R) > 1e-9, R, np.nan))
        own = np.where(np.isfinite(own), own, np.median(np.abs(eq[eq < 0])) if (eq < 0).any() else 20.0)
        wst[t.session.values] = -np.maximum(own, np.maximum(-eq, 0.0))
    return (out, wst) if worst else out


def _combo_inputs(members, w, stops, worsts):
    """Combined account inputs: one 'unit' = w_i micros of each member (w_i ~ equal risk per member). Worst point of a day =
    every member trading that day hits its own stop that day. Returns (pts, worst, unit_risk, micros_per_unit)."""
    pts = sum(wi * m for wi, m in zip(w, members))
    worst = sum(wi * x for wi, x in zip(w, worsts))
    return pts.values, np.asarray(worst.values, dtype=float), float(sum(wi * st for wi, st in zip(w, stops))), int(sum(w))


def _plan_for_units(P, per_unit):
    """The plan's contract limits expressed in units of the combination (a unit trades `per_unit` micros)."""
    Q = dict(P); Q["eval_max_mnq"] = P["eval_max_mnq"] // per_unit
    Q["fund_max_tiers"] = [[lo, m // per_unit] for lo, m in P["fund_max_tiers"]]
    return Q if Q["eval_max_mnq"] >= 1 and Q["fund_max_tiers"][0][1] >= 1 else None


def portfolio_stage(A, X, S, minutes=10.0):
    """Combine 2-4 strategies into one prop account and score the combination.
    Anti-self-deception: members, weights, the combination, plan and sizing are all CHOSEN on the search years 2014-21
    only (members = the best stage-A strategies; pairwise correlation of daily P&L <= 0.3 on 2014-21). The 2022-23
    years are used once, to validate the top combinations (account EV per eval + the 5-account farm), and are reported
    next to each member's own 2022-23 EV. Contracts per unit count against the plan's limits."""
    import itertools as it, prop_sim
    t0 = time.time()
    if not len(A) or "ev" not in A: return []
    pool = A[(A.get("n", 0) >= 150) & (A.ev > 0)].drop_duplicates("spec_id").sort_values("ev", ascending=False)
    D = S.data(); ses = D["M"].session.values
    calA = ses[(ses >= "2014-01-01") & (ses <= SEARCH_END)]; calB = ses[(ses > SEARCH_END) & (ses <= VAL_END)]
    mem = []
    for _, r in pool.iterrows():
        if len(mem) >= PORT_POOL or time.time() - t0 > minutes * 30: break
        try:
            spec = json.loads(r.spec); a, aw = _daily(spec, X, S, calA, worst=True)
        except Exception as e:
            print("portfolio member skipped:", type(e).__name__, e); continue
        if (a != 0).sum() < 150: continue
        if any(abs(np.corrcoef(a, m["a"])[0, 1]) > 0.95 for m in mem): continue      # near-duplicate (mutants)
        neg = np.abs(a[a < 0]); mem.append({"row": r, "spec": spec, "a": a, "aw": aw, "stop": float(np.median(neg)) if len(neg) else 20.0})
    if len(mem) < 2: return []
    C = np.corrcoef(np.vstack([m["a"].values for m in mem]))
    combos = []
    for k in (2, 3, 4):
        for c in it.combinations(range(len(mem)), k):
            if any(abs(C[i, j]) > PORT_MAX_CORR for i, j in it.combinations(c, 2)): continue
            smax = max(mem[i]["stop"] for i in c); w = [max(1, int(round(smax / mem[i]["stop"]))) for i in c]
            u = sum(wi * mem[i]["a"] for wi, i in zip(w, c)); sd = float(u.std())
            combos.append((float(u.mean()) / sd * np.sqrt(252) if sd > 0 else -9, c, w))
    combos = sorted(combos, key=lambda x: -x[0])[:PORT_SCREEN]
    print(f"portfolio stage: {len(mem)} members, {len(combos)} combinations screened"); sys.stdout.flush()
    scored = []
    for sh, c, w in combos:
        if time.time() - t0 > minutes * 60: break
        pts, worst, U, per = _combo_inputs([mem[i]["a"] for i in c], w, [mem[i]["stop"] for i in c], [mem[i]["aw"] for i in c])
        for P in prop_sim.plans().values():
            Q = _plan_for_units(P, per)
            if not Q: continue
            for sz in SIZINGS:
                r = prop_sim.evaluate(pts, worst, Q, S._sizer({"prop": sz}, U), step=8)
                scored.append({"sharpe_A": sh, "c": c, "w": w, "plan": P["id"], "sz": sz, "U": U, "per": per, "A": r})
    best = {}
    for x in sorted(scored, key=lambda x: -x["A"]["ev_per_eval"]):           # best plan/sizing per combination (chosen on A)
        best.setdefault(x["c"], x)
    top = [x for x in sorted(best.values(), key=lambda x: -x["A"]["ev_per_eval"]) if x["A"]["ev_per_eval"] > 0][:PORT_VALIDATE]
    out = []
    for x in top:
        c, w = x["c"], x["w"]; P = prop_sim.plans()[x["plan"]]; Q = _plan_for_units(P, x["per"])
        try:
            bs = [_daily(mem[i]["spec"], X, S, calB, worst=True) for i in c]
        except Exception as e:
            print("portfolio validation skipped:", e); continue
        pts, worst, _, _ = _combo_inputs([b[0] for b in bs], w, [mem[i]["stop"] for i in c], [b[1] for b in bs])
        size = S._sizer({"prop": x["sz"]}, x["U"])
        vb = prop_sim.evaluate(pts, worst, Q, size, step=4)
        f = prop_sim.farm(pts, worst, calB, Q, size, slots=5)
        out.append({"date": datetime.now(timezone.utc).date().isoformat(), "members": " + ".join(mem[i]["row"]["name"][:60] for i in c),
                    "spec_ids": ",".join(mem[i]["row"]["spec_id"] for i in c), "weights": ",".join(map(str, w)),
                    "markets": ",".join(mem[i]["spec"].get("market", "NQ") for i in c), "micros_per_unit": x["per"],
                    "max_corr_A": round(float(max(abs(C[i, j]) for i, j in it.combinations(c, 2))), 2), "sharpe_A": round(x["sharpe_A"], 2),
                    "plan": x["plan"], "risk": x["sz"]["risk"], "eval_risk": x["sz"]["eval_risk"],
                    "pass_A": x["A"]["pass_rate"], "ev_A": x["A"]["ev_per_eval"], "pass_B": vb["pass_rate"], "paid_B": vb["avg_payout_per_eval"],
                    "ev_B": vb["ev_per_eval"], "farm_month_B": f["avg_month"], "farm_pos_months_B": f["positive_months"], "farm_worst_B": f["worst_month"],
                    "best_member_ev_A": max(float(mem[i]["row"]["ev"]) for i in c),
                    "members_ev_B": ",".join("" if pd.isna(mem[i]["row"].get("ev_val")) else f"{float(mem[i]['row']['ev_val']):.0f}" for i in c)})
    if out:
        old = pd.read_csv(PORT) if os.path.exists(PORT) else pd.DataFrame()
        pd.concat([old, pd.DataFrame(out)], ignore_index=True).to_csv(PORT, index=False)
    print(f"portfolio stage: {len(out)} combinations validated in {(time.time() - t0) / 60:.1f} min")
    return out


def portfolio_lines(new=None):
    """Status lines: the best combinations so far, ranked by 2022-23 EV (validation only, never used to choose)."""
    P = pd.read_csv(PORT) if os.path.exists(PORT) else pd.DataFrame()
    if not len(P): return []
    P = P.sort_values("date").drop_duplicates(["spec_ids", "plan", "risk"], keep="last").sort_values("ev_B", ascending=False)
    lines = ["", f"PORTFOLIOS (2-4 low-correlation strategies in ONE account; chosen on 2014-21, validated on 2022-23; {len(P)} combinations validated so far):"]
    for _, r in P.head(3).iterrows():
        lines.append(f"- {r.members[:150]} | {r.plan} risk {r.risk:.0%}/{r.eval_risk:.0%}, {int(r.micros_per_unit)} micros/unit, max corr {r.max_corr_A:.2f} "
                     f"| 2014-21 EV {r.ev_A:+.0f} (pass {r.pass_A:.0%}, best single {r.best_member_ev_A:+.0f}) | 2022-23 EV {r.ev_B:+.0f} (pass {r.pass_B:.0%}) "
                     f"| 5 accounts: {r.farm_month_B:+.0f}$/month ({r.farm_pos_months_B:.0%} months positive)")
    return lines


BASE_FOCUS = {"NQ": 0.50, "GC": 0.25, "CL": 0.25}           # the owner's starting split
PREF = os.path.join(OUT, "preferences.json")


EXAM_MIN = 3          # locked exams (all markets together) before exam results start steering the focus
FWD_MIN = 20          # forward-test trades in a market before live results count


def exam_evidence():
    """Per market: locked exams taken and passed (knowledge/strategies.jsonl, every source), and the live forward test of
    exam-passed strategies (knowledge/strategy_forward.csv: trades, total R, t-stat of the mean R)."""
    ev = {m: {"exams": 0, "passed": 0, "fwd_trades": 0, "fwd_R": 0.0, "fwd_t": 0.0} for m in MARKETS}
    f = os.path.join(K, "strategies.jsonl")
    for l in (open(f) if os.path.exists(f) else []):
        try:
            e = json.loads(l)
        except Exception:
            continue
        if not (e.get("exam") or e.get("prop_exam")): continue          # only entries that actually sat the locked exam
        m = ((e.get("spec") or {}).get("market") or "NQ").upper()
        if m not in ev: continue
        ev[m]["exams"] += 1; ev[m]["passed"] += int(str(e.get("verdict", "")).startswith("PROMISING STRATEGY"))
    fw = os.path.join(K, "strategy_forward.csv")
    try:
        F = pd.read_csv(fw); F = F[F.traded.astype(bool)]
        for m, g in F.groupby(F.get("market", pd.Series("NQ", index=F.index)).fillna("NQ")):
            if m in ev and len(g):
                sd = float(g.R.std(ddof=1)) if len(g) > 1 else 0.0
                ev[m].update(fwd_trades=int(len(g)), fwd_R=round(float(g.R.sum()), 2),
                             fwd_t=round(float(g.R.mean() / (sd / np.sqrt(len(g)))), 2) if sd > 0 else 0.0)
    except Exception:
        pass
    return ev


def preferences(A=None, save=False, EV=None):
    """Volta's market focus. Starts at the owner's split (NQ 50 / GC 25 / CL 25). Once every market has 300+ tested
    strategies, the split follows the evidence: each market's smoothed rate of strategies that stayed positive on the
    unseen 2022-23 years, boosted by how good its best validated payouts are. Every market keeps at least 10% so Volta
    never stops exploring; the focus moves gradually (at most halfway to the new target per run).
    Luck control: once every market has a luck bar, "held up" means beat that market's luck bar (not just EV > 0), and
    the payout boost uses the EV above the bar - so a market cannot win focus with lucky 2022-23 survivors.
    Exams and live results dominate (from EXAM_MIN exams on, even before the 300-strategy mark): a market's locked-exam
    pass rate (shrunk towards the pooled rate, 3 pseudo-exams) enters at full weight, while the 2022-23 evidence fades to
    the power 1/(1 + exams/4); a market with FWD_MIN+ live forward trades of exam-passed strategies is scaled by
    2**clip(t/2, -1, 1) (t = t-stat of the live mean R), i.e. up to x2 or /2."""
    A = all_results() if A is None else A
    old = json.load(open(PREF)) if os.path.exists(PREF) else {"weights": dict(BASE_FOCUS), "history": []}
    EV = exam_evidence() if EV is None else EV
    E_tot = sum(v["exams"] for v in EV.values())
    if (not len(A) or "spec" not in A) and E_tot < EXAM_MIN:
        return old if "why" in old else {**old, "why": "owner's starting split - not enough results yet"}
    if len(A) and "spec" in A:
        mk = market_of(A); L = luck(A); use_bar = all(L[m]["bar"] is not None for m in MARKETS)
        xs = excess(A, L) if use_bar else A.get("ev_val", pd.Series(dtype=float))
    else:
        mk = pd.Series(dtype=object); use_bar = False; xs = pd.Series(dtype=float)
    stats = {}
    for m in MARKETS:
        a = A[mk == m] if len(mk) else A.iloc[0:0]; ev = xs[mk == m] if len(xs) else pd.Series(dtype=float); evp = ev[ev > 0] if len(a) else ev
        stats[m] = {"tested": int(len(a)), "validated": int((ev > 0).sum()) if len(a) else 0,
                    "top5": float(evp.sort_values(ascending=False).head(5).mean()) if len(evp) else 0.0, **EV[m]}
    val_ready = min(v["tested"] for v in stats.values()) >= 300
    if not val_ready and E_tot < EXAM_MIN:
        w = dict(old["weights"]); why = "owner's starting split until every market has 300+ tested strategies (" + \
            ", ".join(f"{m} {v['tested']}" for m, v in stats.items()) + f") or {EXAM_MIN}+ locked exams are taken ({E_tot} so far)"
    else:
        if val_ready:
            rate = {m: (v["validated"] + 1) / (v["tested"] + 50) for m, v in stats.items()}; mr = np.mean(list(rate.values()))
            val = {m: (rate[m] / mr) * (1 + max(stats[m]["top5"], 0) / 200) for m in MARKETS}
        else:
            val = {m: 1.0 for m in MARKETS}
        a_val = 1.0 / (1.0 + E_tot / 4.0)                    # 2022-23 survivors fade as locked-exam results accumulate
        pool = (sum(v["passed"] for v in EV.values()) + 0.5) / (E_tot + 3)
        er = {m: (EV[m]["passed"] + 3 * pool) / (EV[m]["exams"] + 3) for m in MARKETS}; emr = np.mean(list(er.values()))
        fwd = {m: 2 ** float(np.clip(EV[m]["fwd_t"] / 2, -1, 1)) if EV[m]["fwd_trades"] >= FWD_MIN else 1.0 for m in MARKETS}
        perf = {m: val[m] ** a_val * (er[m] / emr) * fwd[m] for m in MARKETS}
        tgt = {m: BASE_FOCUS[m] * perf[m] for m in MARKETS}; t = sum(tgt.values()); tgt = {m: v / t for m, v in tgt.items()}
        w = {m: 0.5 * old["weights"].get(m, BASE_FOCUS[m]) + 0.5 * tgt[m] for m in MARKETS}
        w = {m: max(v, 0.10) for m, v in w.items()}; t = sum(w.values()); w = {m: round(float(v / t), 3) for m, v in w.items()}
        why = "evidence: " + ", ".join(
            f"{m} " + (f"{stats[m]['validated']}/{stats[m]['tested']} " + ("beat the luck bar on 2022-23" if use_bar else "held up on 2022-23")
                       + (f" (top EV {'above the bar ' if use_bar else ''}{stats[m]['top5']:+.0f})" if stats[m]["top5"] else "") + "; "
                       if val_ready else "") + f"locked exams {EV[m]['passed']}/{EV[m]['exams']} passed"
            + (f"; live {EV[m]['fwd_trades']} trades {EV[m]['fwd_R']:+.1f}R" if EV[m]["fwd_trades"] else "") for m in MARKETS) \
            + f" (exam weight x1, 2022-23 weight ^{a_val:.2f})"
    out = {"weights": w, "why": why, "stats": stats, "luck_control": use_bar, "history": (old.get("history") or [])[-60:]}
    if save:
        moved = [m for m in MARKETS if abs(w[m] - old["weights"].get(m, BASE_FOCUS[m])) >= 0.10]
        out["history"].append({"date": datetime.now(timezone.utc).date().isoformat(), "weights": w})
        out["shifted"] = moved
        json.dump(out, open(PREF, "w"), indent=1)
    return out


EXLOG = os.path.join(OUT, "exams.csv")


def exam_ledger():
    """spec_id -> latest locked-exam verdict of the prop search (all jobs' candidates; written by job 1 only)."""
    if not os.path.exists(EXLOG): return {}
    E = pd.read_csv(EXLOG); return dict(zip(E.spec_id, E.verdict))


def all_results():
    import glob
    fs = sorted(glob.glob(os.path.join(OUT, "results_*.csv"))) + ([os.path.join(OUT, "results.csv")] if os.path.exists(os.path.join(OUT, "results.csv")) else [])
    return pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def tot_ok(R):
    return len(R) > 0


def write_status(R, gsize, st, tried, validated, exams, pref=None, L=None):
    E1 = R[R.get("metric", pd.Series(index=R.index, dtype=object)) == "edge-v1"] if tot_ok(R) else R.iloc[0:0]
    tot = len(R)
    a = E1[(E1.get("n", 0) >= MIN_TRADES) & (E1.get("edge_lb10", -1) > 0)] if len(E1) else E1
    v = E1[E1.get("edge_lb10_val", pd.Series(index=E1.index, dtype=float)) > 0] if len(E1) else E1
    L = L if L is not None else luck(R)
    xs = excess(R, L); v = v.assign(_x=xs.reindex(v.index)) if len(v) else v.assign(_x=pd.Series(dtype=float))
    lines = [("PROP STRATEGY SEARCH" if TRACK == "classic" else "NEW-REGIME PROP SEARCH (since 2024)") + f" - run {st['nights']} (job {SHARD + 1}/{SHARDS}): {tried} new strategies this run, {tot:,} tested in total "
             f"({len(E1):,} with the edge metric; grid {gsize:,} + mutations, markets {', '.join(SEARCH_MARKETS)})",
             f"Ranked on EDGE (mean net R per trade, bootstrap 10th percentile > 0), prop EV only prices it. "
             f"Stage A ({LBL_A}, edge > 0 with 90% confidence): {len(a)} | Stage B (edge still > 0 on unseen {LBL_B}): {len(v)} | "
             f"exams taken: {len(exam_ledger())}",
             f"LUCK BAR (best {LBL_B} edge that many no-edge random-entry twins reach, {LUCK_CONF:.0%}): " + " | ".join(
                 f"{m} {x['bar']:+.3f}R at {x['validated']} validated tries ({x['null_draws']} placebos, avg {x['null_mean']:+.3f}R) -> {x['beat_luck']} beat it"
                 if x["bar"] is not None else f"{m} not yet ({x['null_draws']} placebos, need {NULL_MIN})" for m, x in L.items() if m in SEARCH_MARKETS)]
    if len(v):
        lines += ["", f"LEADERBOARD (edge on unseen {LBL_B} above the luck bar; 'luck-level' = not above it):"]
        v = v.assign(_r=v._x.fillna(v.edge_val - 1e6)) if v._x.notna().any() else v.assign(_r=v.edge_val)
        for _, r in v.sort_values("_r", ascending=False).head(6).iterrows():
            tag = "" if pd.isna(r._x) else (f" | BEATS LUCK by {r._x:+.3f}R" if r._x > 0 else " | luck-level")
            px = f" | priced: {r.plan} EV {r.ev_val:+.0f}$/eval" if pd.notna(r.get("ev_val")) and isinstance(r.get("plan"), str) else ""
            lines.append(f"- {r['name'][:70]} | {LBL_A} {r.avg_R:+.3f}R (t {r.edge_t:.1f}, {int(r.n)} trades) | {LBL_B} {r.edge_val:+.3f}R "
                         f"(t {r.edge_t_val:.1f}){tag}{px}")
    else:
        lines += ["", f"No strategy has a proven edge on the unseen {LBL_B} years yet."]
    try:
        lines += portfolio_lines()
    except Exception as e:
        print("portfolio lines skipped:", e)
    for name, vd in exams:
        lines += ["", f"EXAM: {name[:70]} -> {vd[:260]}"]
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s[STATUS_KEY] = lines; json.dump(s, open(STATUS, "w"), indent=1)
    if SHARD == 0:
        try:
            import eta; lines += [""] + eta.update()             # Volta's own estimate of when it finds a real edge
        except Exception as e:
            print("eta skipped:", type(e).__name__, e)
    print("\n".join(lines))
    try:
        import test_engine as TE
        ann = json.load(open(TE.ANN)) if os.path.exists(TE.ANN) else []
        passed = [n for n, vd in exams if str(vd).startswith("PROMISING STRATEGY")]
        title = "🏁 Volta found a prop strategy that passed the locked exam" if passed else "🔎 Volta's prop search"
        if not passed and SHARD != 0: return                  # one routine note per run (job 1), always announce a pass
        note_f = os.path.join(OUT, "last_note.txt"); today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not passed and os.path.exists(note_f) and open(note_f).read().strip() == today: return   # routine note once a day
        open(note_f, "w").write(today)
        ann.append({"title": title, "body": "\n".join(lines)[:1800]}); json.dump(ann, open(TE.ANN, "w"), indent=1)
    except Exception as e:
        print("announce skipped:", e)


if __name__ == "__main__":
    if "--portfolio" in sys.argv:                              # run only the portfolio stage on the stored results
        import test_engine as TE, strategy_lab as S
        _, X = TE.frame(); portfolio_stage(all_results(), X, S, minutes=float(os.environ.get("PORTFOLIO_MINUTES", "10")))
        print("\n".join(portfolio_lines()))
    else:
        main()
