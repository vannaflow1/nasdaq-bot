"""tools/london_study.py - does a London-session BIAS for NQ carry information? (owner request 26 Oct 2026: he trades London too)

PRE-DECLARED before any number was looked at (committed first). Background: F15 (London noise-band BREAKOUT as a prop
strategy with stops/targets/costs) failed (all 50 variants negative). This is a different question - a direction lean,
no costs - but the prior is low.
  Data    : owner's full-session NQ 1-minute 2014 - Jan 2026 (om.days), Chicago time grid.
  Session : London open = 08:00 London time (always 09:00 Luxembourg), converted to Chicago per day (DST-exact).
            London end for the outcome = 08:29 CT (the minute before the NY cash open).
  Signal  : the bias.py rule moved to London: anchor = price at the London open; band at minute t = 1.2 x mean
            |c/anchor - 1| at the same elapsed minute over the last 14 sessions; LONG above, SHORT below, else NONE.
            Checks at +60, +120, +180, +240 minutes after the London open (10:00-13:00 Lux).
  Targets : L1 rest-of-London direction: sign(price 08:29 CT - price at check); hit = band side == that sign.
            L2 rest-of-NY-day as well: sign(14:59 CT close - price at check).
            L3 London size: |08:29 CT / London open - 1| vs Asia range z (Asia high-low 17:00 CT -> London open over the
               median of the last 20) - a size forecast for the London session, like the NY outlook.
  Test    : day-level sign-flip permutation (one coin per day flips all that day's band sides), 20,000 draws, on the hit
            rate minus 0.5 - i.e. 'better than a coin flip given the same days and checks'. Also compared to the drift
            baseline (share of checks where rest-of-London is up / down).
  Rule    : design 2014-2021, holdout 2022-Jan 2026 looked at ONCE. A London bias goes live only if the design p < 0.01 and
            the holdout has the same sign with p < 0.05. L3 (size) the same. Otherwise reported as 'no edge' and not posted
            as a bias.
Run: python tools/london_study.py design    then    python tools/london_study.py holdout"""
import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import om
OUT = os.path.join(HERE, "knowledge", "research_out")
CT, LON = ZoneInfo("America/Chicago"), ZoneInfo("Europe/London")
CHECKS = (60, 120, 180, 240); END, CLOSE = om.m_of(8, 29), om.m_of(14, 59)


def lon_open_idx(d):
    t = datetime(d.year, d.month, d.day, 8, 0, tzinfo=LON).astimezone(CT)
    return om.m_of(t.hour, t.minute)


def build():
    D = om.days(); dates = pd.to_datetime(D["dates"]); O, H, L, C = D["o"], D["h"], D["l"], D["c"]; ok = D["have"] > 900
    days = [i for i in range(len(dates)) if ok[i]]; rows = []; size = []
    for j, i in enumerate(days):
        a = lon_open_idx(dates[i].date()); anc = float(O[i, a])
        if j >= 20:
            asia = [(float(H[k, :a].max() - L[k, :a].min()) / float(O[k, lon_open_idx(dates[k].date())])) for k in days[j - 20:j]]
            z = float((H[i, :a].max() - L[i, :a].min()) / anc) / np.median(asia)
            size.append((dates[i], z, abs(float(C[i, END]) / anc - 1)))
        if j < 14: continue
        hist = days[j - 14:j]
        for e in CHECKS:
            t = a + e - 1
            if t >= END: continue
            sig = float(np.mean([abs(C[k, lon_open_idx(dates[k].date()) + e - 1] / O[k, lon_open_idx(dates[k].date())] - 1) for k in hist]))
            c = float(C[i, t]); b = 1 if c > anc * (1 + 1.2 * sig) else -1 if c < anc * (1 - 1.2 * sig) else 0
            rows.append((dates[i], e, b, np.sign(float(C[i, END]) - c), np.sign(float(C[i, CLOSE]) - c)))
    B = pd.DataFrame(rows, columns=["date", "e", "band", "rest_lon", "rest_day"])
    S = pd.DataFrame(size, columns=["date", "asia_z", "lon_move"])
    return B, S


def signflip(b, col, draws=20000, seed=11):
    x = b[b.band != 0].copy(); x["s"] = x.band * x[col]               # +1 right, -1 wrong, 0 flat
    per = x.groupby("date").s.sum().to_numpy(float); n = len(x); obs = per.sum() / n
    rng = np.random.default_rng(seed); null = np.array([(per * rng.choice([-1, 1], len(per))).sum() / n for _ in range(draws)])
    hit = float((x.s > 0).mean())
    return {"checks": int(n), "days": int(len(per)), "hit_rate": round(hit, 4), "edge_score": round(float(obs), 4),
            "p_one_sided": round(float((null >= obs).mean() + 1 / draws), 5),
            "long_hit": round(float((x[x.band == 1].s > 0).mean()), 4), "n_long": int((x.band == 1).sum()),
            "short_hit": round(float((x[x.band == -1].s > 0).mean()), 4), "n_short": int((x.band == -1).sum()),
            "drift_up_share_all_checks": round(float((b[col] > 0).mean()), 4)}


def run(lo, hi):
    B, S = build(); b = B[(B.date >= lo) & (B.date <= hi)]; s = S[(S.date >= lo) & (S.date <= hi)].dropna()
    rs = np.corrcoef(s.asia_z, s.lon_move)[0, 1]; rng = np.random.default_rng(2)
    null = np.array([np.corrcoef(s.asia_z, rng.permutation(s.lon_move.to_numpy()))[0, 1] for _ in range(5000)])
    q = pd.qcut(s.asia_z.rank(method="first"), 5, labels=False)
    out = {"period": [lo, hi], "L1_rest_of_london": signflip(b, "rest_lon"), "L2_rest_of_day": signflip(b, "rest_day"),
           "L1_by_check": {int(e): signflip(b[b.e == e], "rest_lon", draws=5000)["hit_rate"] for e in CHECKS},
           "L3_size": {"corr": round(float(rs), 4), "p": round(float((np.abs(null) >= abs(rs)).mean() + 1 / 5000), 4),
                       "median_move_pct_by_asia_quintile": {str(k): round(float(v) * 100, 3) for k, v in s.groupby(q.values).lon_move.median().items()},
                       "asia_z_cuts": [round(float(x), 2) for x in np.percentile(s.asia_z, [20, 40, 60, 80])]}}
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "design"
    lo, hi = ("2014-01-01", "2021-12-31") if mode == "design" else ("2022-01-01", "2099-12-31")
    r = run(lo, hi); os.makedirs(OUT, exist_ok=True); json.dump(r, open(os.path.join(OUT, f"london_{mode}.json"), "w"), indent=1)
    print(json.dumps(r, indent=1))
