"""tools/selection_check.py - does picking a family's best variant on 2014-21 carry over to 2022-23? (report only)

Idea from the probability-of-backtest-overfitting literature (Bailey, Borwein, Lopez de Prado & Zhu 2014, "The
probability of backtest overfitting"; found again via quantleak.zip, 27 Nov 2026). Volta already controls multiplicity
ACROSS families (Bonferroni, placebo null v3, frozen forward tests); this checks the step INSIDE a family: the best
variant is chosen on the search years (A = 2014-21) and then relied on. If that choice is mostly luck, the chosen
variant's rank on the validation years (B = 2022-23) is no better than a coin flip.

Per family grid (knowledge/research_out/family_F*.csv with edge_A and edge_B per variant):
  - spearman: rank correlation of edge_A and edge_B across variants
  - best_A_pct_B: the A-best variant's percentile among variants on B (1.0 = also best on B, 0.5 = median)
  - logit: log(w / (1 - w)) with w = that percentile (CSCV's lambda for a single A/B split); <= 0 means "below median"
Across families: pbo_like = share of families whose A-best variant lands at or below the B median.

Caveats (printed with the result): one split per family, not the full combinatorial CSCV; families sharing a mechanism
(F2, F10, F12, F13) are not independent; nothing here changes a gate, a verdict or a frozen design.
Run: python tools/selection_check.py   -> knowledge/research_out/selection_check.json"""
import glob, json, math, os, re
import numpy as np, pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "knowledge", "research_out")


def check_family(path):
    d = pd.read_csv(path)
    if not {"edge_A", "edge_B"} <= set(d.columns): return None
    d = d.dropna(subset=["edge_A", "edge_B"])
    if len(d) < 5: return None
    i = int(d["edge_A"].values.argmax())
    rb = d["edge_B"].rank(method="average").values
    w = (rb[i] - 0.5) / len(d)                                  # percentile in (0, 1)
    rho = spearmanr(d["edge_A"], d["edge_B"]).correlation
    return {"variants": len(d), "spearman": round(float(rho), 3),
            "best_A_edge_A": round(float(d["edge_A"].iloc[i]), 4), "best_A_edge_B": round(float(d["edge_B"].iloc[i]), 4),
            "median_edge_B": round(float(d["edge_B"].median()), 4),
            "best_A_pct_B": round(float(w), 3), "logit": round(math.log(w / (1 - w)), 3)}


def run():
    fams = {}
    for p in sorted(glob.glob(os.path.join(OUT, "family_F*.csv")), key=lambda s: int(re.findall(r"F(\d+)", s)[-1])):
        r = check_family(p)
        if r: fams[re.findall(r"(F\d+)", os.path.basename(p))[0]] = r
    lg = [v["logit"] for v in fams.values()]
    res = {"what": "In-family selection check (A = 2014-21 picks the best variant, B = 2022-23 judges it). Report only.",
           "families": fams, "n_families": len(fams),
           "pbo_like": round(float(np.mean([x <= 0 for x in lg])), 3) if lg else None,
           "median_spearman": round(float(np.median([v["spearman"] for v in fams.values()])), 3) if fams else None,
           "caveats": ["one A/B split per family, not full CSCV",
                       "F2, F10, F12, F13 share one mechanism, so they are not independent",
                       "report only: no gate, verdict, frozen design or alpha slot is changed by this"]}
    json.dump(res, open(os.path.join(OUT, "selection_check.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    r = run()
    for k, v in r["families"].items():
        print(f"{k:4s} n={v['variants']:2d} spearman={v['spearman']:+.2f} A-best on B: pct={v['best_A_pct_B']:.2f} "
              f"edge_B={v['best_A_edge_B']:+.4f} (median {v['median_edge_B']:+.4f})")
    print(f"families={r['n_families']} pbo_like={r['pbo_like']} median_spearman={r['median_spearman']}")
