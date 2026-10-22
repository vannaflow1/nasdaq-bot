"""eval_decision.py - the evaluator of the FROZEN eval rule (knowledge/frozen/eval_rule.json; expert review 3 + 4).

What would one prop evaluation with F10 be worth TODAY, given everything known about F10's true edge?
  1. EV curves (weekly, or when missing): F10's frozen forward variant on its 2022-now trades is the SHAPE (stops, skew,
     trades per day, streaks); its true net edge is set by shifting every trade's R. For each plan x sizing x edge,
     prop_sim.Account runs block-bootstrapped account paths (10-day blocks, 250 sessions) -> pass rate, P(pass within
     21 sessions), P(payout), median days, EV per eval (payouts x split x reliability - fee).
     Saved: knowledge/research_out/eval_ev_curves.json.
  2. Daily: the belief about the edge = the frozen posterior (prior N(0, 0.05^2), validation at half weight) updated with
     F10's clean forward trades (families.json F10.forward). 30% a year chance the edge breaks to 0 over an account's
     life. E[EV], P(EV > 0) and - the honest comparison - what F10 ADDS over the same account traded with ZERO edge
     (the published Lucid payout rules make patient low-size trading roughly a free option, so EV > 0 alone proves nothing).
  3. The frozen preconditions decide whether an eval may start; the owner decides whether one does.
Run: python eval_decision.py [--curves]"""
import json, os, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
CURVES = os.path.join(K, "research_out", "eval_ev_curves.json"); OUT = os.path.join(K, "research_out", "eval_decision.json")
PLANS = ("lucid_flex_25k", "lucid_pro_25k", "lucid_flex_50k", "lucid_pro_50k")
SIZINGS = (0.08, 0.12, 0.2)                                   # share of the buffer risked per trade (eval_finish on)
EDGES = (-0.10, -0.05, 0.0, 0.03, 0.05, 0.08, 0.11, 0.15, 0.20)
PATHS, BLOCK, HORIZON = 1500, 10, 250
BREAK_PER_YEAR = 0.30
EXTRA_COMM_PTS = 0.25   # expert review 4: Lucid charges $0.50/side = $1.00 per MNQ round trip; the engine's cost model has $0.50
                        # (0.25 NQ points). The missing 0.25 points per trade is charged HERE only - the frozen forward test keeps
                        # its own cost model. EDGES therefore mean "net edge under the engine's costs", before this extra cost.


def shape(fid="F10"):
    """F10's frozen forward variant on 2022-now: per-trade R, own stop (MNQ points), sessions."""
    import strategy_lab as S, test_engine as TE, families as FA
    _, X = TE.frame(); fam = next(f for f in json.load(open(FA.REG)) if f["id"] == fid)
    v = FA.variants(fam)[int(fam["forward_variant"])]
    T = FA.trades(S, X, v["sleeve"], "2022-01-01", "2099-12-31").sort_values(["session", "k"]).reset_index(drop=True)
    M = S.data("NQ")["M"]; eq = T.pnl.to_numpy(float) * float(M.attrs.get("pv", 2.0)) / 2.0; R = T.R.to_numpy(float)
    st = np.abs(eq / np.where(np.abs(R) > 1e-9, R, np.nan)); st = np.where(np.isfinite(st), st, np.nanmedian(st))
    ses = M.session.values; ses = ses[(ses >= T.session.min()) & (ses <= T.session.max())]
    return T, R, st, ses


def day_series(T, R, st, ses, edge):
    pnl = (R - R.mean() + edge) * st - EXTRA_COMM_PTS; worst = -np.maximum(st, np.maximum(-pnl, 0.0))
    g = pd.DataFrame({"s": T.session.values, "p": pnl, "w": worst}).groupby("s").sum()
    pts = pd.Series(0.0, index=ses); pts[g.index] = g.p.values; wst = pd.Series(0.0, index=ses); wst[g.index] = g.w.values
    return pts.to_numpy(), np.where(pts.to_numpy() != 0, np.minimum(wst.to_numpy(), -1e-9), 0.0)


def run_paths(pts, wst, P, size_fn, seed=0):
    import prop_sim as PS
    rng = np.random.default_rng(seed); n = len(pts); rows = []
    for _ in range(PATHS):
        idx = np.concatenate([np.arange(s, s + BLOCK) % n for s in rng.integers(0, n, HORIZON // BLOCK + 1)])[:HORIZON]
        a = PS.Account(P); pday = None; paid = 0.0; fpay = None; life = HORIZON
        for d, i in enumerate(idx):
            got = a.step(pts[i], wst[i], size_fn); paid += got
            if got > 0 and fpay is None: fpay = d + 1
            if getattr(a, "passed_now", False): a.passed_now = False; pday = d + 1
            if a.end is not None: life = d + 1; break
        rows.append((pday, paid, fpay, life))
    pd_ = np.array([r[0] or np.nan for r in rows], float); paid = np.array([r[1] for r in rows]); fp = np.array([r[2] or np.nan for r in rows], float)
    return {"pass_rate": round(float(np.isfinite(pd_).mean()), 3), "pass_within_21": round(float((pd_ <= 21).mean()), 3),
            "median_days_to_pass": None if not np.isfinite(pd_).any() else int(np.nanmedian(pd_)),
            "p_payout": round(float((paid > 0).mean()), 3),
            "median_days_to_first_payout": None if not np.isfinite(fp).any() else int(np.nanmedian(fp)),
            "median_account_life_days": int(np.median([r[3] for r in rows])),
            "ev_per_eval": round(float(paid.mean() - P["fee"]), 1), "ev_se": round(float(paid.std() / np.sqrt(len(paid))), 1)}


def curves():
    import strategy_lab as S, prop_sim as PS
    T, R, st, ses = shape(); plans = PS.plans(True); med = float(np.median(st)); out = {"date": datetime.now(timezone.utc).date().isoformat(), "extra_comm_pts": EXTRA_COMM_PTS,
        "shape": f"F10 forward variant, {len(T)} trades 2022-now, observed mean {R.mean():+.3f}R (sd {R.std():.2f}), median stop {med:.1f} MNQ pts",
        "paths": PATHS, "horizon_sessions": HORIZON, "rows": []}
    series = {e: day_series(T, R, st, ses, e) for e in EDGES}
    for plan in PLANS:
        for risk in SIZINGS:
            fn = S._sizer({"target": {"R": 5}, "prop": {"risk": risk, "eval_risk": risk, "eval_finish": True}}, med)
            for e in EDGES:
                pts, wst = series[e]
                out["rows"].append({"plan": plan, "risk": risk, "edge": e, **run_paths(pts, wst, plans[plan], fn, seed=int(risk * 1000))})
    json.dump(out, open(CURVES, "w"), indent=1); return out


def belief():
    """Frozen posterior + clean forward trades (as computed by families.forward_route each evening)."""
    d = json.load(open(os.path.join(K, "frozen", "F10_forward_design.json"))); pv = d["posterior"]["validation"]
    fam = next(f for f in json.load(open(os.path.join(K, "families.json"))) if f["id"] == "F10"); fw = fam.get("forward") or {}
    if fw.get("posterior_mean") is not None and int(fw.get("n", 0)) > 0:
        return float(fw["posterior_mean"]), float(fw["posterior_sd"]), int(fw["n"]), fw
    vv = pv["se"] ** 2 / pv["weight"]; prec = 1 / 0.05 ** 2 + 1 / vv; mu = (pv["edge"] / vv) / prec
    return float(mu), float(prec ** -0.5), 0, fw


def main():
    stale = not os.path.exists(CURVES) or (time.time() - os.path.getmtime(CURVES)) > 6.5 * 86400
    try: stale = stale or json.load(open(CURVES)).get("extra_comm_pts") != EXTRA_COMM_PTS   # cost model changed -> recompute
    except Exception: stale = True
    C = curves() if ("--curves" in sys.argv or stale) else json.load(open(CURVES))
    rule = json.load(open(os.path.join(K, "frozen", "eval_rule.json")))
    mu, sd, n_fwd, fw = belief(); rng = np.random.default_rng(1); draws = rng.normal(mu, sd, 20000)
    df = pd.DataFrame(C["rows"]); res = []
    for (plan, risk), g in df.groupby(["plan", "risk"]):
        g = g.sort_values("edge"); E = g.edge.to_numpy(float); V = g.ev_per_eval.to_numpy(float)
        life_yr = float(g[g.edge == 0.0].median_account_life_days.iloc[0]) / 252.0
        p_break = 1 - (1 - BREAK_PER_YEAR) ** life_yr
        d_eff = np.where(rng.random(len(draws)) < p_break, 0.0, draws)
        ev = np.interp(d_eff, E, V); base = float(np.interp(0.0, E, V)); row0 = g[g.edge == 0.0].iloc[0]
        rowm = g.iloc[int(np.argmin(np.abs(E - mu)))]
        res.append({"plan": plan, "risk": risk, "E_ev": round(float(ev.mean()), 1), "P_ev_gt_0": round(float((ev > 0).mean()), 3),
                    "zero_edge_ev": round(base, 1), "f10_adds": round(float(ev.mean()) - base, 1),
                    "pass_within_21_at_belief": float(rowm.pass_within_21), "median_days_to_pass_at_belief": rowm.median_days_to_pass,
                    "median_days_to_first_payout_at_belief": rowm.median_days_to_first_payout, "p_payout_at_belief": float(rowm.p_payout),
                    "p_break_over_account_life": round(p_break, 3)})
    R = pd.DataFrame(res).sort_values("E_ev", ascending=False); best = R.iloc[0].to_dict()
    fast = R[R.pass_within_21_at_belief >= 0.2].sort_values("E_ev", ascending=False)
    sim_ok = False                                            # precondition 1: SIM execution path (not built yet)
    z = fw.get("z"); fwd_ok = n_fwd >= 60 and (z is None or float(z) > -1.645)
    stop = fw.get("decision") in ("STOPPED (futility)", "STOPPED (CUSUM kill)", "NOT CONFIRMED") or (n_fwd > 0 and float(fw.get("p_edge_pos", 1)) < 0.5)
    crit = rule["start_eval_when"]; meets = best["E_ev"] > crit["E_ev_per_eval_gt"] and best["P_ev_gt_0"] > crit["P_ev_gt_0_gt"]
    verdict = ("STOP - a frozen stop condition fired" if stop else
               "NOT YET - preconditions unmet (" + ", ".join(x for x, ok in (("SIM execution path >= 20 sessions", sim_ok),
               (f">= 60 clean forward trades ({n_fwd} so far)", fwd_ok)) if not ok) + ")" if not (sim_ok and fwd_ok) else
               ("ALLOWED by the frozen rule (the owner decides)" if meets else "NO - expected value criterion not met"))
    out = {"date": datetime.now(timezone.utc).date().isoformat(), "extra_comm_pts": EXTRA_COMM_PTS, "belief": {"mean": round(mu, 4), "sd": round(sd, 4), "forward_trades": n_fwd},
           "verdict": verdict, "best": best, "best_fast": fast.iloc[0].to_dict() if len(fast) else None, "all": R.to_dict("records"),
           "curves_date": C.get("date"), "note": "EV from published Lucid rules as modelled in prop_firms.json; zero_edge_ev = the same account with no edge"}
    json.dump(out, open(OUT, "w"), indent=1, default=float)
    b = best; lines = [
        f"🎟️ EVAL RULE (frozen) - {verdict}",
        f"Belief about F10's net edge: {mu:+.3f}R ± {sd:.3f} ({n_fwd} clean forward trades).",
        f"Best account: {b['plan']} at risk {b['risk']:.2f} of the buffer per trade - E[EV] {b['E_ev']:+.0f}$/eval, P(EV>0) {b['P_ev_gt_0']:.0%}; "
        f"the same account with ZERO edge {b['zero_edge_ev']:+.0f}$ -> F10 adds {b['f10_adds']:+.0f}$. "
        f"Median {b['median_days_to_pass_at_belief']} sessions to pass, {b['median_days_to_first_payout_at_belief']} to a first payout.",
    ]
    if len(fast):
        f = fast.iloc[0]; lines.append(f"Fastest with >= 20% passing inside a month: {f['plan']} risk {f['risk']:.2f} - E[EV] {f['E_ev']:+.0f}$/eval "
                                       f"(zero edge {f['zero_edge_ev']:+.0f}$), {f['pass_within_21_at_belief']:.0%} pass within 21 sessions.")
    s = json.load(open(os.path.join(HERE, "status.json"))) if os.path.exists(os.path.join(HERE, "status.json")) else {}
    s["eval_rule"] = lines; json.dump(s, open(os.path.join(HERE, "status.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
