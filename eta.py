"""eta.py - Volta's own estimate of WHEN it finds a profitable prop algo, from its own progress.

The goal (owner, 21 Oct 2026): an algorithm that PASSES prop-firm evaluations and keeps GENERATING PAYOUTS - measured in
Volta's prop simulator on years it never saw. Live/forward trading is deliberately NOT part of this goal.
"Found" = a strategy that (1) passes the full prop protocol including the LOCKED 2024-2026 exam (payouts minus fees > 0
on unseen years, beats random entries, survives double costs) AND (2) is judged CONFIRMED - not luck - by the weekly
review (strategies.jsonl field "review": "CONFIRMED: ..." / "FRAGILE: ..." / "FLUKE: ...").

How the estimate works (Monte Carlo over 4000 possible worlds, each weighted by how well it explains Volta's history):
  1. Does a real, findable prop edge exist in what Volta searches at all? Nobody knows: prior 50/50. Every failed exam
     and every exam-passer the review rejects makes "no" more likely; a CONFIRMED one makes it certain.
  2. If one exists, what share of locked exams is taken by a REAL edge? Prior Beta(1, 19) - about 1 in 20 (most search
     survivors are luck: Harvey, Liu & Zhu 2016; Bailey et al. 2014). A lucky (no-edge) candidate still passes the
     exam LUCK_PASS = 25% of the time - which is why the review step exists.
  3. The review recognises a real edge REAL_CONFIRM = 85% of the time; it happens every Sunday.
  4. Exams per week = Volta's actual exam rate (smoothed toward 2/week until it has history, capped at the weekly
     exam budget). Exam-passers waiting for review count with their own chance of being real.
Every unknown is drawn from its uncertainty, so the result is a RANGE, not a promise. It changes as results come in.
Writes status.json["eta"] (shown at the top of /search and /wishes) and knowledge/eta_history.csv.
Keep it honest: never tune the priors to make the number look better."""
import json, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATUS, HIST = os.path.join(HERE, "status.json"), os.path.join(K, "eta_history.csv")
P_EXISTS, PRIOR_REAL, LUCK_PASS, REAL_CONFIRM = 0.5, (1.0, 19.0), 0.25, 0.85
SIMS, MAX_WEEKS = 4000, 520


def _jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def _review(e):
    r = str(e.get("review") or "").upper()
    return "confirmed" if r.startswith("CONFIRMED") else "rejected" if r.startswith(("FRAGILE", "FLUKE", "REJECT")) else "waiting"


def inputs():
    import strategy_lab as S
    E = _jl(S.LOG)
    exams = [e for e in E if "LOCKED EXAM" in str(e.get("verdict", ""))]
    passed = list({S.spec_id(e["spec"]): e for e in exams if str(e.get("verdict", "")).startswith("PROMISING STRATEGY")}.values())
    dates = sorted({e["date"] for e in E if e.get("source") == "prop-search"} | {e["date"] for e in exams})
    first = pd.Timestamp(dates[0]) if dates else pd.Timestamp(datetime.now(timezone.utc).date())
    days = max(1.0, (pd.Timestamp(datetime.now(timezone.utc).date()) - first).days + 1)
    rate = min(S.EXAMS_PER_WEEK, (len(exams) + 4) / (days + 14) * 7)     # smoothed toward 2 exams/week until there is history
    cands = [{"name": e["name"], "status": _review(e), "ev": (e.get("prop_exam") or {}).get("ev_per_eval"),
              "plan": (e.get("prop_exam") or {}).get("plan")} for e in passed]
    return {"exams": len(exams), "passes": len(passed), "rate": rate, "days_running": int(days), "cands": cands,
            "rejected": sum(c["status"] == "rejected" for c in cands), "confirmed": sum(c["status"] == "confirmed" for c in cands)}


def simulate(I, seed=7):
    """Weeks until the first CONFIRMED prop algo, per simulated world (inf = not within 10 years / none exists)."""
    rng = np.random.default_rng(seed)
    if I["confirmed"]:
        return np.zeros(SIMS)
    exists = rng.random(SIMS) < P_EXISTS
    pi = np.where(exists, rng.beta(*PRIOR_REAL, SIMS), 0.0)                 # share of exams that catch a real edge
    p_real = pi / (pi + (1 - pi) * LUCK_PASS)                                 # P(real | passed the exam)
    fails = I["exams"] - I["passes"]
    w = (1 - pi) ** fails * (1 - REAL_CONFIRM * p_real) ** I["rejected"]   # likelihood of what Volta has seen
    idx = rng.choice(SIMS, SIMS, p=w / w.sum()); pi, p_real = pi[idx], p_real[idx]
    rate = rng.gamma(4 + I["exams"], I["rate"] / (4 + I["exams"]), SIMS)
    to_sunday = ((6 - datetime.now(timezone.utc).weekday()) % 7 + 1) / 7    # weeks until the next review (Sunday)
    eta = np.full(SIMS, np.inf)
    for c in I["cands"]:                                                    # exam-passers waiting for their review
        if c["status"] != "waiting": continue
        ok = rng.random(SIMS) < p_real * REAL_CONFIRM
        eta = np.where(ok, np.minimum(eta, to_sunday), eta)
    for wk in range(MAX_WEEKS):
        live = eta > wk + to_sunday
        if not live.any(): break
        real = rng.binomial(rng.poisson(rate), pi)
        found = rng.binomial(real, REAL_CONFIRM) > 0
        eta = np.where(live & found, np.minimum(eta, wk + 1 + to_sunday), eta)   # passes this week, confirmed next Sunday
    return eta


def _fmt(weeks):
    if not np.isfinite(weeks): return "more than 10 years"
    if weeks < 1: return "under a week"
    if weeks < 9: return f"{weeks:.0f} weeks"
    return f"{weeks / 4.35:.0f} months" if weeks < 104 else f"{weeks / 52:.1f} years"


def lines(I=None):
    I = I or inputs(); eta = simulate(I)
    fin = np.isfinite(eta); p = lambda wk: float((eta <= wk).mean()); cond = eta[fin]
    out = ["⏳ WHEN WILL I HAVE A PROP ALGO THAT PASSES EVALS AND KEEPS PAYING OUT? (my own estimate - a range, not a promise)"]
    if I["confirmed"]:
        out.append("FOUND: " + "; ".join(c["name"][:70] for c in I["cands"] if c["status"] == "confirmed") + " - passed the locked exam and the review.")
        return out
    if len(cond):
        out.append(f"If there is one to find: most likely in {_fmt(np.median(cond))} (80% range {_fmt(np.percentile(cond, 10))} to "
                   f"{_fmt(np.percentile(cond, 90))}). Overall chance within 1 month {p(4.35):.0%}, 3 months {p(13):.0%}, 6 months {p(26):.0%}, 1 year {p(52):.0%}.")
    out.append(f"Chance there is NO such algo in what I search (or I never catch it): {1 - fin.mean():.0%}. Honest: most strategy "
               f"searches find nothing; each failed exam nudges this up, a confirmed algo ends it.")
    out.append(f"Based on: {I['exams']} locked exams in {I['days_running']} days ({I['passes']} passed, {I['rejected']} rejected by review), "
               f"about {I['rate']:.1f} exams/week. 'Found' = passes evals and pays out on unseen 2024-26 in my simulator AND the review says it isn't luck.")
    w = [c for c in I["cands"] if c["status"] == "waiting"]
    out.append("Waiting for Sunday's review: " + "; ".join(f"{c['name'][:55]} (exam EV {c['ev']:+.0f}$/eval on {c['plan']})" for c in w)
               if w else "Nothing waiting for review.")
    out.append("Assumptions until I have more history: 50/50 that such an algo exists here; if it does, ~1 in 20 exams catches it; "
               "a lucky strategy still passes the exam 1 in 4 times; the review spots a real one 85% of the time.")
    return out


def update():
    I = inputs(); L = lines(I)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L; json.dump(s, open(STATUS, "w"), indent=1)
    eta = simulate(I); fin = np.isfinite(eta)
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "exams": I["exams"], "passes": I["passes"],
                         "rejected": I["rejected"], "median_weeks_if_exists": round(float(np.median(eta[fin])), 1) if fin.any() else None,
                         "p_none": round(float((~fin).mean()), 3), "p_3m": round(float((eta <= 13).mean()), 3), "p_1y": round(float((eta <= 52).mean()), 3)}])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines()))
