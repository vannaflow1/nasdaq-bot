"""
brain_retrain.py - monthly self-improvement. Refits the brain on its whole memory
(history + every graded live day). The new version only replaces the old one if it
does at least as well on the most recent 120 days it was NOT trained on.
"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import brain, qqq_gex_daily as q

HOLD = 120


def ridge(X, y, alpha):
    mu, ym = X.mean(0), y.mean()
    Xc = X - mu
    b = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(X.shape[1]), Xc.T @ (y - ym))
    return float(ym - mu @ b), b


def main():
    m = json.load(open(brain.MODEL))
    F = m["features"]
    mem = pd.read_csv(brain.MEM, parse_dates=["date"]).dropna(subset=F + ["y_rng"]).sort_values("date")
    X, y = mem[F].to_numpy(float), np.log(mem.y_rng.clip(lower=1e-5).to_numpy(float))
    tr, te = slice(0, len(mem) - HOLD), slice(len(mem) - HOLD, None)
    i_new, b_new = ridge(X[tr], y[tr], m["alpha"])
    miss = lambda i, b: float(np.mean(np.abs(np.exp(y[te]) - np.exp(i + X[te] @ b))) * 100)
    m_new, m_old = miss(i_new, b_new), miss(m["intercept"], np.array(m["coef"]))
    n_live = int((mem.date > "2025-12-31").sum())
    if m_new <= m_old:
        i_all, b_all = ridge(X, y, m["alpha"])
        major, minor = m["version"].split(".")
        m.update(version=f"{major}.{int(minor) + 1}", intercept=i_all, coef=[float(c) for c in b_all],
                 trained=f"{mem.date.min():%Y-%m} .. {mem.date.max():%Y-%m}")
        json.dump(m, open(brain.MODEL, "w"), indent=1)
        title = f"Brain upgraded to v{m['version']}"
        body = (f"Retrained on {len(mem):,} days of memory ({n_live} of them live).\n"
                f"Test on the last {HOLD} days: new {m_new:.3f}% avg miss vs old {m_old:.3f}% -> promoted.")
    else:
        title = f"Brain stays on v{m['version']}"
        body = (f"Tried retraining on {len(mem):,} days ({n_live} live). On the last {HOLD} days the new version "
                f"missed {m_new:.3f}% vs {m_old:.3f}% for the current one -> kept the current brain.")
    print(title); print(body)
    from datetime import datetime
    if m_new <= m_old or datetime.now().weekday() == 4:      # daily now: post upgrades always, "kept" only on Fridays
        q.push(title, body, tags="brain", hook=os.environ.get("DISCORD_WEBHOOK_BRAIN") or None)


if __name__ == "__main__":
    main()
