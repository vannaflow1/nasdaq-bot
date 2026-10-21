"""eta.py - Volta's own estimate of WHEN it will find something truly beneficial, from its own progress.

"Truly beneficial" = a strategy that (1) passes the locked 2024-2026 exam AND (2) then holds up for FORWARD_DAYS trading
days of real forward testing (strategy_forward.py, rules fixed before each day) with a positive result. Only that is
worth real money.

How the estimate works (a small Monte Carlo over 4000 possible worlds, each weighted by how well it explains Volta's
own history so far):
  1. Does a real, findable edge exist in what Volta searches at all? Nobody knows: prior 50/50. Every failed exam and
     every failed forward test makes "no" a bit more likely; a success makes "yes" certain.
  2. If one exists, what share of locked exams is taken by a REAL edge? Prior Beta(1, 19) - about 1 in 20 (most search
     survivors are luck: Harvey, Liu & Zhu 2016; Bailey et al. 2014). A lucky (no-edge) candidate still passes the
     exam LUCK_PASS = 25% of the time - that is why an exam pass alone is not enough.
  3. A real edge survives the FORWARD_DAYS forward test 80% of the time (a real but small edge can still have a bad
     quarter); a lucky one is not counted as found.
  4. Exams per week = Volta's actual exam rate (smoothed with 2/week until it has a few weeks of history, capped at the
     lab's weekly budget). Strategies already in forward testing count with the days they have left.
Writes status.json["eta"] (shown under /search and /wishes) and knowledge/eta_history.csv."""
import json, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATUS, HIST = os.path.join(HERE, "status.json"), os.path.join(K, "eta_history.csv")
FORWARD_DAYS = 60                    # ~3 months of real forward trading before Volta calls an edge "real"
P_EXISTS, PRIOR_REAL, LUCK_PASS, REAL_HOLD = 0.5, (1.0, 19.0), 0.25, 0.8
SIMS, MAX_WEEKS = 4000, 520


def _jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def inputs():
    import strategy_lab as S
    E = _jl(S.LOG)
    exams = [e for e in E if "LOCKED EXAM" in str(e.get("verdict", ""))]
    passed = [e for e in exams if str(e.get("verdict", "")).startswith("PROMISING STRATEGY")]
    dates = sorted({e["date"] for e in E if e.get("source") == "prop-search"} | {e["date"] for e in exams})
    first = pd.Timestamp(dates[0]) if dates else pd.Timestamp(datetime.now(timezone.utc).date())
    days = max(1.0, (pd.Timestamp(datetime.now(timezone.utc).date()) - first).days + 1)
    cap = S.EXAMS_PER_WEEK
    rate = min(cap, (len(exams) + 4) / (days + 14) * 7)               # smoothed toward 2 exams/week until there is history
    F = pd.read_csv(os.path.join(K, "strategy_forward.csv")) if os.path.exists(os.path.join(K, "strategy_forward.csv")) else pd.DataFrame()
    fwd = []
    for e in {S.spec_id(e["spec"]): e for e in passed}.values():
        f = F[F.id == S.spec_id(e["spec"])] if len(F) else F
        n = int(f.date.nunique()) if len(f) else 0; R = float(f.R.sum()) if len(f) else 0.0
        fwd.append({"name": e["name"], "days": n, "R": R, "done": n >= FORWARD_DAYS, "held": n >= FORWARD_DAYS and R > 0})
    done = [f for f in fwd if f["done"]]
    return {"exams": len(exams), "passes": len(passed), "rate": rate, "days_running": int(days), "forward": fwd,
            "hold_n": len(done), "hold_ok": sum(f["held"] for f in done)}


def simulate(I, seed=7):
    """Weeks until the first REAL edge is confirmed, per simulated world (inf = not within 10 years / none exists)."""
    rng = np.random.default_rng(seed)
    if any(f["held"] for f in I["forward"]):
        return np.zeros(SIMS)
    exists = rng.random(SIMS) < P_EXISTS
    pi = np.where(exists, rng.beta(*PRIOR_REAL, SIMS), 0.0)                 # share of exams that catch a real edge
    p_real_given_pass = pi / (pi + (1 - pi) * LUCK_PASS)
    fails = I["exams"] - I["passes"]
    fwd_failed = I["hold_n"] - I["hold_ok"]
    # weight each world by the likelihood of what Volta has seen (failed exams, failed forward tests)
    w = (1 - pi) ** fails * (1 - REAL_HOLD * p_real_given_pass) ** fwd_failed
    idx = rng.choice(SIMS, SIMS, p=w / w.sum())
    pi, p_real_given_pass = pi[idx], p_real_given_pass[idx]
    rate = rng.gamma(4 + I["exams"], I["rate"] / (4 + I["exams"]), SIMS)
    fw_weeks = FORWARD_DAYS / 5
    eta = np.full(SIMS, np.inf)
    for f in I["forward"]:                                                  # candidates already in their forward test
        if f["done"]: continue
        ok = rng.random(SIMS) < p_real_given_pass * REAL_HOLD
        eta = np.where(ok, np.minimum(eta, (FORWARD_DAYS - f["days"]) / 5), eta)
    for wk in range(MAX_WEEKS):
        live = eta > wk + fw_weeks
        if not live.any(): break
        real = rng.binomial(rng.poisson(rate), pi)
        found = rng.binomial(real, REAL_HOLD) > 0
        eta = np.where(live & found, np.minimum(eta, wk + 1 + fw_weeks), eta)
    return eta


def _fmt(weeks):
    if not np.isfinite(weeks): return "more than 10 years"
    if weeks < 1: return "now"
    if weeks < 9: return f"{weeks:.0f} weeks"
    return f"{weeks / 4.35:.0f} months" if weeks < 104 else f"{weeks / 52:.1f} years"


def lines(I=None):
    I = I or inputs(); eta = simulate(I)
    fin = np.isfinite(eta); p = lambda wk: float((eta <= wk).mean())
    cond = eta[fin]
    out = ["⏳ WHEN WILL I FIND A REAL EDGE? (my own estimate - a range, not a promise)"]
    if len(cond):
        out.append(f"If there is one to find: most likely in {_fmt(np.median(cond))} (80% range {_fmt(np.percentile(cond, 10))} to "
                   f"{_fmt(np.percentile(cond, 90))}). Overall chance within 6 months {p(26):.0%}, 1 year {p(52):.0%}, 3 years {p(156):.0%}.")
    out.append(f"Chance there is NO real edge in what I search (or I never catch it): {1 - fin.mean():.0%}. That is honest - "
               f"most strategy searches find nothing; each failed exam nudges this up, a confirmed edge ends it.")
    out.append(f"Based on: {I['exams']} locked exams in {I['days_running']} days ({I['passes']} passed), about {I['rate']:.1f} exams/week, "
               f"and {FORWARD_DAYS} trading days (~3 months) of forward testing before anything counts as real.")
    out.append("In forward testing now: " + "; ".join(f"{f['name'][:55]} ({f['days']}/{FORWARD_DAYS} days, {f['R']:+.1f}R)" for f in I["forward"])
               if I["forward"] else "Nothing in forward testing yet.")
    out.append(f"Assumptions until I have my own history: 50/50 that an edge exists here; if it does, ~1 in 20 exams catches it; "
               f"a lucky no-edge strategy still passes the exam 1 in 4 times. Forward tests finished: {I['hold_ok']}/{I['hold_n']} held.")
    return out


def update():
    I = inputs(); L = lines(I)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L; json.dump(s, open(STATUS, "w"), indent=1)
    eta = simulate(I)
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "exams": I["exams"], "passes": I["passes"],
                         "median_weeks_if_exists": round(float(np.median(eta[np.isfinite(eta)])), 1) if np.isfinite(eta).any() else None,
                         "p_none": round(float((~np.isfinite(eta)).mean()), 3),
                         "p_3m": round(float((eta <= 13).mean()), 3), "p_1y": round(float((eta <= 52).mean()), 3)}])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines()))
