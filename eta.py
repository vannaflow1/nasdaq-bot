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
  3. The review (review_prop.py: placebo on the unseen years, stability in 4 periods, nudges, costs - run IMMEDIATELY
     after an exam pass, double-checked by Claude's nightly session) recognises a real edge REAL_CONFIRM = 85% of the time.
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
    cands = [{"name": e["name"], "status": _review(e), "ev": ((e.get("review_detail") or {}).get("recent") or {}).get("2024-26 exam") or (e.get("prop_exam") or {}).get("ev_per_eval"), "why": str(e.get("review") or ""),
              "plan": (e.get("prop_exam") or {}).get("plan")} for e in passed]
    return {"exams": len(exams), "passes": len(passed), "rate": rate, "days_running": int(days), "cands": cands,
            "rejected": sum(c["status"] == "rejected" for c in cands), "confirmed": sum(c["status"] == "confirmed" for c in cands)}


def simulate(I, seed=7):
    """Weeks until the first CONFIRMED prop algo, per simulated world (inf = not within 10 years / none exists)."""
    rng = np.random.default_rng(seed)
    prior_real = I.get("prior_real", PRIOR_REAL)
    exists = rng.random(SIMS) < (1.0 if I["confirmed"] else P_EXISTS)       # one confirmed -> such algos exist here
    pi = np.where(exists, rng.beta(*prior_real, SIMS), 0.0)
    p_real = pi / (pi + (1 - pi) * LUCK_PASS)                                 # P(real | passed the exam)
    fails = I["exams"] - I["passes"]
    w = (1 - pi) ** fails * (1 - REAL_CONFIRM * p_real) ** I["rejected"]   # likelihood of what Volta has seen
    idx = rng.choice(SIMS, SIMS, p=w / w.sum()); pi, p_real = pi[idx], p_real[idx]
    rate = np.minimum(rng.gamma(4 + I["exams"], I["rate"] / (4 + I["exams"]), SIMS), I.get("rate_cap", 10))
    to_sunday = 0.0                                                         # the review runs right after the exam (since 21 Oct)
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
        out.append("FOUND: " + "; ".join(f"{c['name'][:60]} (exam {c['ev']:+.0f}$/eval on {c['plan']}, under regime watch)" for c in I["cands"] if c["status"] == "confirmed")
                   + ". NEXT GOAL: a second, independent algo - two uncorrelated algos pay out far more steadily than one.")
    if len(cond) and I["confirmed"]:
        out.append(f"Next one: most likely in {_fmt(np.median(cond))} (80% range {_fmt(np.percentile(cond, 10))} to {_fmt(np.percentile(cond, 90))}); "
                   f"chance within 1 month {p(4.35):.0%}, 3 months {p(13):.0%}, 1 year {p(52):.0%}.")
    elif len(cond):
        out.append(f"If there is one to find: most likely in {_fmt(np.median(cond))} (80% range {_fmt(np.percentile(cond, 10))} to "
                   f"{_fmt(np.percentile(cond, 90))}). Overall chance within 1 month {p(4.35):.0%}, 3 months {p(13):.0%}, 6 months {p(26):.0%}, 1 year {p(52):.0%}.")
    if not I["confirmed"]:
        out.append(f"Chance there is NO such algo in what I search (or I never catch it): {1 - fin.mean():.0%}. Honest: most strategy "
                   f"searches find nothing; each failed exam nudges this up, a confirmed algo ends it.")
    out.append(f"Based on: {I['exams']} locked exams in {I['days_running']} days ({I['passes']} passed, {I['rejected']} rejected by review), "
               f"about {I['rate']:.1f} exams/week. 'Found' = passes evals and pays out on unseen 2024-26 in my simulator AND the review says it isn't luck.")
    w = [c for c in I["cands"] if c["status"] == "waiting"]
    out.append("Waiting for review: " + "; ".join(f"{c['name'][:55]} (exam EV {c['ev']:+.0f}$/eval on {c['plan']})" for c in w)
               if w else "Nothing waiting for review.")
    out.append("Assumptions until I have more history: 50/50 that such an algo exists here; if it does, ~1 in 20 exams catches it; "
               "a lucky strategy still passes the exam 1 in 4 times; the review (right after each exam) spots a real one 85% of the time.")
    rv = [c for c in I["cands"] if c["status"] == "rejected"]
    if rv: out.append("Rejected by review: " + "; ".join(f"{c['name'][:55]} ({c['why'][:110]})" for c in rv[-2:]))
    return out


def levers(I=None):
    """What would move my timer most? What-if versions of the estimate (the real estimate never uses them).
    Honest levers only: more good candidates reaching the exam, and better candidates. Never: more exams on the same
    locked years (the weekly cap protects the exam from being overfit), weaker reviews, or tuned priors."""
    import strategy_lab as S
    I = I or inputs()
    def score(J):
        eta = simulate(J); return float((eta <= 13).mean()), float((eta <= 52).mean())
    base = score(I)
    sc = {"more candidates reach the exam (2x exam rate: more search, more markets, portfolios)": dict(I, rate=min(S.EXAMS_PER_WEEK, I["rate"] * 2)),
          "better candidates (2x hit rate: ideas from papers/hunts that fit the CURRENT regime, new data)": dict(I, prior_real=(2.0, 19.0)),
          "both": dict(I, rate=min(S.EXAMS_PER_WEEK, I["rate"] * 2), prior_real=(2.0, 19.0))}
    res = {k: score(J) for k, J in sc.items()}
    best = max([k for k in res if k != "both"], key=lambda k: res[k][1])
    out = [f"MY TIMER LEVERS (what-if): now {base[0]:.0%} within 3 months / {base[1]:.0%} within 1 year."]
    out += [f"- {k}: {v[0]:.0%} / {v[1]:.0%}" for k, v in res.items()]
    out.append(f"Biggest single lever right now: {best.split(' (')[0]}. Exam rate today {I['rate']:.1f}/week of max {S.EXAMS_PER_WEEK} "
               f"({'room to grow' if I['rate'] < S.EXAMS_PER_WEEK * 0.8 else 'near the cap - only better candidates help'}).")
    return out


def update():
    I = inputs(); L = lines(I)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L
    try: s["eta_levers"] = levers(I)
    except Exception as e: print("levers skipped:", e)
    json.dump(s, open(STATUS, "w"), indent=1)
    eta = simulate(I); fin = np.isfinite(eta)
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "exams": I["exams"], "passes": I["passes"],
                         "rejected": I["rejected"], "median_weeks_if_exists": round(float(np.median(eta[fin])), 1) if fin.any() else None,
                         "p_none": round(float((~fin).mean()), 3), "p_3m": round(float((eta <= 13).mean()), 3), "p_1y": round(float((eta <= 52).mean()), 3)}])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines())); print(); print("\n".join(levers()))
