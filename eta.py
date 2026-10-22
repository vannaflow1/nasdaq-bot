"""eta.py v3 - Volta's own estimate for F10, the one live candidate (expert review 3, 22 Oct 2026).

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
SIMS, DAYS, RATE, SD = 4000, 520, 0.98, 2.07           # ~2 years of trading days


def _posterior(d, n_f=0, mean_f=0.0):
    v = d["posterior"]["validation"]; vv = v["se"] ** 2 / v["weight"]; pf = n_f / SD ** 2
    prec = 1 / 0.05 ** 2 + 1 / vv + pf
    return (v["edge"] / vv + mean_f * pf) / prec, prec ** -0.5


def _forward_so_far():
    try:
        F = json.load(open(os.path.join(K, "families.json"))); f = next(x for x in F if x["id"] == "F10")
        fw = f.get("forward") or {}
        return int(fw.get("n") or 0), float(fw.get("edge") or 0.0), f.get("status"), fw.get("decision")
    except Exception:
        return 0, 0.0, None, None


def simulate(seed=7):
    from statistics import NormalDist
    import sealed
    N = NormalDist(); d = json.load(open(DESIGN)); rng = np.random.default_rng(seed)
    n0, m0, status, dec = _forward_so_far()
    mu, sd = _posterior(d, n0, m0); delta = rng.normal(mu, sd, SIMS)
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
        pm, ps = _posterior(d, 0, 0)
        v = d["posterior"]["validation"]; vv = v["se"] ** 2 / v["weight"]; pf = n / SD ** 2; prec = 1 / 0.0025 + 1 / vv + pf
        post_mu = (v["edge"] / vv + (S / np.maximum(n, 1)) * pf) / prec
        eff = 0.7 * post_mu                                  # 30%/year regime-break risk (eval rule): edge -> 0 in those worlds
        p02 = 1 - np.array([N.cdf(x) for x in (0.02 - eff) * np.sqrt(prec) / 0.7])
        r = alive & (n >= 60) & (p02 > 0.6) & np.isinf(ready); ready[r] = day
    return {"delta_mu": mu, "delta_sd": sd, "kill": kill, "conf": conf, "ready": ready, "n0": n0, "status": status, "dec": dec}


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
    r = simulate(); L = lines(r)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L; s.pop("eta_levers", None)
    json.dump(s, open(STATUS, "w"), indent=1)
    m = lambda months: months * 21
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "model": "v3-F10",
                         "edge_mu": round(r["delta_mu"], 4), "n_forward": r["n0"],
                         "p_ready_6m": round(float((r["ready"] <= m(6)).mean()), 3), "p_kill_12m": round(float((r["kill"] <= m(12)).mean()), 3),
                         "p_conf_24m": round(float((r["conf"] <= m(24)).mean()), 3)}])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines()))
