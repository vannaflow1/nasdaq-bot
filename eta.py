"""eta.py v4 - Volta's own estimate for the families in forward test: F10 and (since 15 Nov 2026) F13.
(v3, expert review 3, 22 Oct 2026, covered F10 only. F12 is not listed separately: it is nested in F10 and has taken the
same trades so far. F13 uses exactly the same method with ITS OWN frozen design file - nothing here is tuned:
trade rate = validation trades / 1011 trading days in the 2022-01..2026-01 window (the 0.98 a day v3 used for F10),
noise per trade = the design file's cp_sd_per_trade_R, forward posterior sd = max(that, 1.5) as the design declares.)

After review 3 the honest picture is: a frequentist proof of a +0.08R edge at ~1 trade a day takes years, so the forward
test's realistic job is to KILL F10 if it is dead, and to feed a Bayesian eval-decision rule (knowledge/frozen/eval_rule.json).
This timer simulates F10's forward route, world by world:
  * true edge per trade drawn from F10's CURRENT posterior: prior N(0, 0.05R) + validation (+0.108R, se 0.060) at half
    weight + every clean forward trade so far (knowledge/frozen/F10_forward_design.json),
  * trades arrive at F10's real rate (0.98 per trading day, Poisson), noise 2.07R per trade,
  * the frozen design decides: futility looks at 100/200/300 trades (conditional power < 1%), O'Brien-Fleming backstop
    up to 600 trades (CUSUM kill not simulated - it fires rarely within a year for a live edge),
  * "eval-ready" = the statistical half of the eval rule: >= 60 forward trades, not stopped, posterior P(0.7 x edge > 0.02R) > 0.6
    (0.7 = the eval rule's 30%/year regime-break risk; 0.02R ~ costs of a real eval's fills; the SIM execution precondition is NOT counted - it is not built yet).
Writes status.json["eta"] and knowledge/eta_history.csv. Never tune the inputs to make the numbers look better."""
import json, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATUS, HIST = os.path.join(HERE, "status.json"), os.path.join(K, "eta_history.csv")
DESIGN = os.path.join(K, "frozen", "F10_forward_design.json")
SIMS, DAYS, RATE, SD = 4000, 520, 0.98, 2.07           # ~2 years of trading days; RATE/SD are F10's (kept for reference)
FAMILIES = ("F10", "F13")                              # families with a frozen forward design that are tracked here
VAL_DAYS = 1011                                        # trading days in the validation window (991 F10 trades / 0.98 a day)
NAMES = {"F10": "Nasdaq noise-band breakout", "F13": "the same breakout with quick fixed targets and re-entries"}


def _design(fam):
    return json.load(open(os.path.join(K, "frozen", f"{fam}_forward_design.json")))


def _params(fam, d):
    """(trades per trading day, noise per trade in R, sd used for the forward part of the posterior) for one family."""
    if fam == "F10": return RATE, SD, SD
    sd = float(d["futility"]["cp_sd_per_trade_R"])
    return d["posterior"]["validation"]["n"] / VAL_DAYS, sd, max(sd, 1.5)


def _posterior(d, n_f=0, mean_f=0.0, sd_f=SD):
    v = d["posterior"]["validation"]; vv = v["se"] ** 2 / v["weight"]; pf = n_f / sd_f ** 2
    prec = 1 / 0.05 ** 2 + 1 / vv + pf
    return (v["edge"] / vv + mean_f * pf) / prec, prec ** -0.5


def _forward_so_far(fam="F10"):
    try:
        F = json.load(open(os.path.join(K, "families.json"))); f = next(x for x in F if x["id"] == fam)
        fw = f.get("forward") or {}
        return int(fw.get("n") or 0), float(fw.get("edge") or 0.0), f.get("status"), fw.get("decision")
    except Exception:
        return 0, 0.0, None, None


def simulate(seed=7, fam="F10"):
    from statistics import NormalDist
    import sealed
    N = NormalDist(); d = _design(fam); rng = np.random.default_rng(seed)
    RATE, SD, SD_POST = _params(fam, d)                    # shadow the F10 defaults with this family's own numbers
    n0, m0, status, dec = _forward_so_far(fam)
    mu, sd = _posterior(d, n0, m0, SD_POST); delta = rng.normal(mu, sd, SIMS)
    nmax = d["efficacy"]["n_max"]; bounds = sealed.obf_bounds(d["efficacy"]["looks"], d["efficacy"]["alpha_one_sided"]); b = bounds[-1]
    fut = d["futility"]; cpth = fut["stop_if_conditional_power_below"]
    S = np.full(SIMS, m0 * n0); n = np.full(SIMS, n0, float)
    kill = np.full(SIMS, np.inf); conf = np.full(SIMS, np.inf); ready = np.full(SIMS, np.inf)
    looks_done = {L: n0 >= L for L in fut["looks_trades"]}
    for day in range(1, DAYS + 1):
        k = rng.poisson(RATE, SIMS); add = k > 0
        S = S + np.where(add, rng.normal(delta * k, SD * np.sqrt(np.maximum(k, 1))), 0.0); n = n + k
        alive = np.isinf(kill) & np.isinf(conf)
        for L in fut["looks_trades"]:                      # futility at L (approximated with the running total)
            hit = alive & (n >= L) & (n - k < L)
            if hit.any():
                m = nmax - n
                cp = 1 - np.array([N.cdf(x) for x in (b * SD * np.sqrt(nmax) - S[hit] - fut["cp_alternative_edge_R"] * m[hit]) / (SD * np.sqrt(np.maximum(m[hit], 1)))])
                kk = np.where(hit)[0][cp < cpth]; kill[kk] = day
        alive = np.isinf(kill) & np.isinf(conf)
        look = np.minimum((n / (nmax / len(bounds))).astype(int), len(bounds))
        z = S / (SD * np.sqrt(np.maximum(n, 1)))
        bz = np.array([bounds[l - 1] if l >= 1 else np.inf for l in look])
        conf[alive & (look >= 1) & (z >= bz)] = day
        # statistical half of the eval rule
        v = d["posterior"]["validation"]; vv = v["se"] ** 2 / v["weight"]; pf = n / SD_POST ** 2; prec = 1 / 0.0025 + 1 / vv + pf
        post_mu = (v["edge"] / vv + (S / np.maximum(n, 1)) * pf) / prec
        eff = 0.7 * post_mu                                  # 30%/year regime-break risk (eval rule): edge -> 0 in those worlds
        p02 = 1 - np.array([N.cdf(x) for x in (0.02 - eff) * np.sqrt(prec) / 0.7])
        r = alive & (n >= 60) & (p02 > 0.6) & np.isinf(ready); ready[r] = day
    return {"delta_mu": mu, "delta_sd": sd, "kill": kill, "conf": conf, "ready": ready, "n0": n0, "status": status, "dec": dec,
            "fam": fam, "rate": RATE}


def lines_f13(r=None):
    """Three lines for F13 (same method as F10, its own frozen design). Shown under the F10 block."""
    r = r or simulate(fam="F13"); p = lambda a, d: float((a <= d).mean()); m = lambda months: months * 21
    from statistics import NormalDist
    need = max(0, 60 - r["n0"]); weeks = need / max(r["rate"], 1e-9) / 5
    return [f"⏳ F13 ({NAMES['F13']}) - same timer, F13's own frozen design. It shares its entries with F10: one bet, not two.",
            f"Belief now: true edge {r['delta_mu']:+.3f}R per trade (± {r['delta_sd']:.3f}), P(edge > 0) "
            f"{1 - NormalDist(r['delta_mu'], r['delta_sd']).cdf(0):.0%}; {r['n0']} clean forward trades so far"
            + (f" (about {weeks:.0f} more weeks to the 60-trade minimum)." if need else " (60-trade minimum reached)."),
            f"Ready for a first eval (statistically; SIM execution check not built): 3 months {p(r['ready'], m(3)):.0%}, 6 months "
            f"{p(r['ready'], m(6)):.0%}, 12 months {p(r['ready'], m(12)):.0%}. Killed as dead: 6 months {p(r['kill'], m(6)):.0%}, "
            f"12 months {p(r['kill'], m(12)):.0%}. Formally proven: 24 months {p(r['conf'], m(24)):.0%}. "
            "F13 did not meet the fast-track speed rule (about $26-31 a month per account at this edge)."]


def lines(r=None):
    r = r or simulate(); p = lambda a, d: float((a <= d).mean()); m = lambda months: months * 21
    out = ["⏳ F10 (Nasdaq noise-band breakout) - WHAT THE COMING MONTHS WILL TELL ME (v3; a range, not a promise)",
           f"Belief now: true edge {r['delta_mu']:+.3f}R per trade (± {r['delta_sd']:.3f}), P(edge > 0) {1 - __import__('statistics').NormalDist(r['delta_mu'], r['delta_sd']).cdf(0):.0%}; "
           f"{r['n0']} clean forward trades so far.",
           f"Ready for a first eval (statistically; the SIM execution check is not built yet): 3 months {p(r['ready'], m(3)):.0%}, "
           f"6 months {p(r['ready'], m(6)):.0%}, 12 months {p(r['ready'], m(12)):.0%}.",
           f"Killed as dead (futility): 6 months {p(r['kill'], m(6)):.0%}, 12 months {p(r['kill'], m(12)):.0%}. "
           f"Formally proven (O'Brien-Fleming): 12 months {p(r['conf'], m(12)):.0%}, 24 months {p(r['conf'], m(24)):.0%}.",
           "Proof of a +0.08R edge at ~1 trade a day takes years; the forward test's real job is to kill F10 early if it is dead "
           "and to feed the frozen eval rule (max 3 evals, one at a time, never on the funded account)."]
    return out


def update():
    r = simulate(); L = lines(r); runs = [("v3-F10", r)]
    try:                                                   # F13 block: never allowed to break the F10 lines
        r13 = simulate(fam="F13"); L = L + [""] + lines_f13(r13); runs.append(("v4-F13", r13))
    except Exception as e:
        print("eta F13 skipped:", type(e).__name__, e)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L; s.pop("eta_levers", None)
    json.dump(s, open(STATUS, "w"), indent=1)
    m = lambda months: months * 21
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "model": model,
                         "edge_mu": round(x["delta_mu"], 4), "n_forward": x["n0"],
                         "p_ready_6m": round(float((x["ready"] <= m(6)).mean()), 3), "p_kill_12m": round(float((x["kill"] <= m(12)).mean()), 3),
                         "p_conf_24m": round(float((x["conf"] <= m(24)).mean()), 3)} for model, x in runs])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines() + [""] + lines_f13()))
