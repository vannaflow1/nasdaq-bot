"""pool_review.py - monthly: re-test all near-miss ideas TOGETHER (knowledge/feature_pool.json).
Honest protocol: choose the best combination (greedy forward selection) on the OLDER test years only, then judge
it on the last 3 years it never saw. Only a win there gets announced and flagged for review - nothing is
switched into the live brain automatically."""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import test_engine as T, idea_lab as I
K = os.path.join(HERE, "knowledge")


def main():
    pool = json.load(open(T.POOL)) if os.path.exists(T.POOL) else []
    if len(pool) < 2: print("pool too small"); return
    M, X = T.frame(); F = {}
    for p in pool:
        name = (p.get("template") or p.get("expr"))[:40]
        try:
            F[name] = T.garch_feature(X, p["template"]) if p.get("template") else T.evaluate(p["expr"], X)
        except Exception as e:
            print("skip", name, e)
    F = pd.DataFrame(F)
    D = I.memory()[I.BASE + ["y_rng"]].join(F, rsuffix="_p").replace([np.inf, -np.inf], np.nan).dropna()
    y = np.log(D.y_rng.clip(lower=1e-5)); yrs = sorted(set(D.index.year)); test = yrs[-3:]; pick = [v for v in yrs[:-3] if v >= yrs[0] + 3]
    def gain(cols, years):
        g = []
        for yr in years:
            tr, te = D.index.year < yr, D.index.year == yr
            m = {}
            for nm, cs in (("b", I.BASE), ("w", I.BASE + cols)):
                i, b = I._ridge(D.loc[tr, cs].values, y[tr].values)
                m[nm] = np.abs(np.exp(y[te].values) - np.exp(i + D.loc[te, cs].values @ b)).mean()
            g.append((m["b"] - m["w"]) / m["b"] * 100)
        return np.array(g)
    chosen, best = [], 0.0
    while True:
        cand = [(gain(chosen + [c], pick).mean(), c) for c in F.columns if c not in chosen]
        if not cand: break
        g, c = max(cand)
        if g <= best + 0.05: break
        chosen, best = chosen + [c], g
    out = {"date": pd.Timestamp.now().date().isoformat(), "pool_size": len(F.columns), "pick_years": pick, "test_years": test,
           "chosen": chosen, "gain_pick": round(best, 2)}
    if chosen:
        gt = gain(chosen, test); out.update(gain_test=[round(v, 2) for v in gt], avg_test=round(float(gt.mean()), 2))
        win = gt.mean() > 0.5 and (gt > 0).sum() >= 2
    else:
        win = False
    out["verdict"] = "PROMISING - flagged for review" if win else "NOT CONFIRMED - the combination does not hold on unseen years"
    json.dump(out, open(os.path.join(K, "pool_review.json"), "w"), indent=1)
    ann = json.load(open(T.ANN)) if os.path.exists(T.ANN) else []
    ann.append({"title": "🧩 Monthly combined test of near-miss ideas",
                "body": f"{len(F.columns)} small-but-consistent ideas re-tested TOGETHER. Best mix picked on {pick[0]}-{pick[-1]}: "
                        f"{', '.join(chosen) or 'none'} ({best:+.2f}%). On {test[0]}-{test[-1]} (never seen): "
                        f"{out.get('avg_test', 0):+.2f}% -> **{out['verdict']}**"})
    json.dump(ann, open(T.ANN, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
