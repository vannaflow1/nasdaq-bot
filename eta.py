"""eta.py v2 - Volta's estimate of WHEN it has a prop algo that passes evals and keeps paying out (expert review 2).

v1 counted exams ("1 in 20 exams catches a real algo"). For the small edges Volta actually finds (~0.03-0.08R per trade,
1.5-2R of noise per trade) the time to success is set by HOW FAST EVIDENCE ACCUMULATES, not by how many exams it takes.
v2 simulates the real pipeline, world by world (Monte Carlo):
  * every family Volta tests has a TRUE edge drawn from a prior: most mass at 0, a tail at 0.03-0.10R
    (P_ZERO, EDGE_TAIL). F2-pool / F2-LV use F2's own evidence instead: validation +0.06R and exam +0.061R over 474
    trades -> about N(+0.025, 0.035) after shrinking (expert review 2).
  * family test: passes with the MEASURED power curve (power.py: twin-null worlds; planted lift -> share found).
  * then either the SEALED exam (if it has >= 70% power) or the GROUP-SEQUENTIAL forward route: every trade is simulated
    with the family's noise per trade and its pooled trade rate; O'Brien-Fleming boundaries at 10 looks up to N_MAX.
  * review recognises a real one REAL_CONFIRM of the time.
  * new families arrive at FAM_PER_WEEK.
Every input that Volta measures (power curve, noise per trade, trades per day, forward results so far) replaces its
default as soon as it exists. Writes status.json["eta"], ["eta_levers"] and knowledge/eta_history.csv.
Keep it honest: never tune the priors to make the number look better."""
import json, os, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATUS, HIST = os.path.join(HERE, "status.json"), os.path.join(K, "eta_history.csv")
SIMS, WEEKS = 3000, 104
P_ZERO, EDGE_TAIL = 0.75, (0.03, 0.10)                       # prior for a NEW family's true edge (R per trade, after costs)
F2_PRIOR = (0.025, 0.035)                                    # F2's own evidence, shrunk (validation + exam, expert review 2)
SD_TRADE, SD_LV, LV_EDGE_SHARE = 1.75, 1.0, 0.7              # noise per trade (F2 exam implied 1.5-2R); low-variance exits
RATE_ONE, MARKETS = 0.9, 3                                   # trades per day per market (F2 on NQ), markets pooled now
FAM_PER_WEEK, REAL_CONFIRM, N_MAX, LOOKS = 0.5, 0.85, 3000, 10
SEALED_DAYS = 170 + 75 + 80                                  # sealed trading days: NQ + GC + CL
POWER_X, POWER_Y = [0.0, 0.03, 0.06, 0.12], [0.01, 0.35, 1.0, 1.0]   # family test: true lift -> P(pass) (power.py, F2)


def _measured():
    """Replace defaults with what Volta has measured."""
    m = {}
    try:
        P = pd.read_csv(os.path.join(K, "research_out", "power.csv")); P = P[P.method == "twin-null-v2"]
        c = P.groupby("delta").passed.mean()
        m["power_x"] = [0.0] + [0.6 * d for d in c.index if d > 0]; m["power_y"] = [float(c.get(0.0, 0.01))] + [float(c[d]) for d in c.index if d > 0]
    except Exception:
        pass
    try:
        F = json.load(open(os.path.join(K, "families.json")))
        m["families"] = [f for f in F if f.get("status") in ("registered", "forward", "awaiting_exam")]
    except Exception:
        m["families"] = []
    return m


def _boundaries():
    try:
        import sealed; return np.array(sealed.obf_bounds(LOOKS))
    except Exception:
        return np.array([5.70, 4.03, 3.29, 2.85, 2.55, 2.33, 2.15, 2.01, 1.90, 1.80])


def _one_family(rng, delta, sd, rate, start_wk, pw_x, pw_y, z_b, n0=0, s0=0.0):
    """Week at which this family yields a CONFIRMED algo (inf = never), per world. delta: true edges (array)."""
    n = len(delta); out = np.full(n, np.inf)
    passed = rng.random(n) < np.interp(np.maximum(delta, 0), pw_x, pw_y) if n0 == 0 else np.ones(n, bool)
    # the sealed never-seen window arrives at once as the first block of the group-sequential test, then the forward days
    n_sealed = rate * SEALED_DAYS / 3 * 0.96                  # SEALED_DAYS is summed over 3 markets; rate is pooled per day
    per_week = rate * 5; info = np.arange(1, LOOKS + 1) * N_MAX / LOOKS
    S = rng.normal(delta * n_sealed, sd * np.sqrt(n_sealed)); m = n_sealed; alive = passed.copy()
    for k, nk in enumerate(info):
        add = max(nk - m, 0)
        if add > 0: S = S + rng.normal(delta * add, sd * np.sqrt(add)); m = nk
        z = S / (sd * np.sqrt(max(nk, m))); wk = start_wk + 1 + max(nk - n_sealed, 0) / per_week
        hit = alive & (z >= z_b[k]) & np.isinf(out)
        out[hit & (rng.random(n) < REAL_CONFIRM)] = wk
        alive &= ~hit
        if k + 1 >= LOOKS / 2: alive &= z >= 0                # futility
    return out


def simulate(cfg=None, seed=7):
    c = dict(rate=RATE_ONE * MARKETS, sd=SD_TRADE, sd_lv=SD_LV, fam_rate=FAM_PER_WEEK, f2=F2_PRIOR)
    c.update(cfg or {})
    rng = np.random.default_rng(seed); m = _measured()
    pw_x, pw_y = m.get("power_x", POWER_X), m.get("power_y", POWER_Y); z_b = _boundaries()
    eta = np.full(SIMS, np.inf)
    d2 = rng.normal(*c["f2"], SIMS)                          # F2 mechanism's true edge, shared by F2-pool and F2-LV
    eta = np.minimum(eta, _one_family(rng, d2, c["sd"], c["rate"], 0.0, pw_x, pw_y, z_b))
    eta = np.minimum(eta, _one_family(rng, LV_EDGE_SHARE * d2, c["sd_lv"], c["rate"], 0.0, pw_x, pw_y, z_b))
    wk = 1.0
    while wk < WEEKS:                                         # new families (generic prior)
        new = rng.random(SIMS) < min(c["fam_rate"], 1.0)
        d = np.where(rng.random(SIMS) < P_ZERO, 0.0, rng.uniform(*EDGE_TAIL, SIMS))
        e = _one_family(rng, d, c["sd"], c["rate"], wk, pw_x, pw_y, z_b)
        eta = np.where(new, np.minimum(eta, e), eta); wk += 1.0
    eta[eta > WEEKS] = np.inf
    return eta


def _fmt(weeks):
    if not np.isfinite(weeks): return "more than 2 years"
    if weeks < 1: return "under a week"
    if weeks < 9: return f"{weeks:.0f} weeks"
    return f"{weeks / 4.35:.0f} months" if weeks < 104 else f"{weeks / 52:.1f} years"


def lines(eta=None):
    eta = simulate() if eta is None else eta
    p = lambda wk: float((eta <= wk).mean()); fin = np.isfinite(eta)
    out = ["⏳ WHEN WILL I HAVE A PROP ALGO THAT PASSES EVALS AND KEEPS PAYING OUT? (v2: built on measured power - a range, not a promise)",
           f"Chance within 1 month {p(4.35):.0%}, 3 months {p(13):.0%}, 6 months {p(26):.0%}, 1 year {p(52):.0%}, 2 years {p(104):.0%}."]
    if fin.any():
        out.append(f"In the worlds where I find one within 2 years: most likely after {_fmt(np.median(eta[fin]))} "
                   f"(80% range {_fmt(np.percentile(eta[fin], 10))} to {_fmt(np.percentile(eta[fin], 90))}).")
    out += [f"Why it is slow: my edges are small (~0.03-0.08R per trade) against ~{SD_TRADE}R of noise per trade. Confirming +0.06R "
            f"needs roughly 4,000-7,000 trades; I make about {RATE_ONE * MARKETS:.1f} trades a day across {MARKETS} markets.",
            "Fastest ways to raise it: more independent trades per day (more markets), less noise per trade (low-variance exits), "
            "and the sealed Feb-Oct 2026 window (one clean shot per family)."]
    return out


def levers():
    base = simulate()
    def sc(cfg):
        e = simulate(cfg); return float((e <= 26).mean()), float((e <= 52).mean())
    b = (float((base <= 26).mean()), float((base <= 52).mean()))
    res = {"2x trades per day (ES/YM/RTY added, more markets)": sc({"rate": RATE_ONE * MARKETS * 2}),
           "half the noise per trade (low-variance exits work)": sc({"sd": SD_TRADE / 2, "sd_lv": SD_LV / 2}),
           "2x families tested per week (good ideas only)": sc({"fam_rate": FAM_PER_WEEK * 2})}
    out = [f"MY TIMER LEVERS (what-if): now {b[0]:.0%} within 6 months / {b[1]:.0%} within 1 year."]
    out += [f"- {k}: {v[0]:.0%} / {v[1]:.0%}" for k, v in res.items()]
    best = max(res, key=lambda k: res[k][1]); out.append(f"Biggest single lever right now: {best}.")
    return out


def update():
    eta = simulate(); L = lines(eta)
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["eta"] = L
    try: s["eta_levers"] = levers()
    except Exception as e: print("levers skipped:", e)
    json.dump(s, open(STATUS, "w"), indent=1)
    row = pd.DataFrame([{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), "model": "v2",
                         "p_1m": round(float((eta <= 4.35).mean()), 3), "p_3m": round(float((eta <= 13).mean()), 3),
                         "p_6m": round(float((eta <= 26).mean()), 3), "p_1y": round(float((eta <= 52).mean()), 3)}])
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, row], ignore_index=True).tail(2000).to_csv(HIST, index=False)
    return L


if __name__ == "__main__":
    print("\n".join(lines())); print(); print("\n".join(levers()))
