"""Do GARCH-family forecasts (GARCH, GJR, EGARCH, t-dist, refit yearly on past data) add to Volta's range brain?"""
import sys, os, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import test_engine as T, idea_lab as I, numpy as np
M, X = T.frame(); X["y"] = np.log(X.y_range / 100); X["vixl"] = np.log(X.vix)
for k in ("garch", "gjr", "egarch"): X[k] = T.garch_feature(X, k)
base = [c for c in I.BASE if c in X] + ["vixl"]; D0 = X.dropna(subset=["y", "garch", "gjr", "egarch"] + base)
def wf(cols):
    e = {}
    for yr in range(2019, 2026):
        tr, te = D0[D0.index.year < yr], D0[D0.index.year == yr]
        b = np.linalg.lstsq(np.c_[np.ones(len(tr)), tr[cols]], tr.y, rcond=None)[0]; e[yr] = ((te.y - np.c_[np.ones(len(te)), te[cols]] @ b) ** 2).mean()
    return e
e0 = wf(base); out = []
for nm, c in (("GARCH", ["garch"]), ("GJR-GARCH", ["gjr"]), ("EGARCH", ["egarch"]), ("all three", ["garch", "gjr", "egarch"])):
    e = wf(base + c); imp = [(1 - e[y] / e0[y]) * 100 for y in e]
    out.append(f"+ {nm:10s} " + " ".join(f"{y}:{v:+.1f}%" for y, v in zip(e, imp)) + f" avg {np.mean(imp):+.2f}%")
for nm in ("garch", "gjr", "egarch"):
    e = wf([nm]); out.append(f"{nm} alone: avg out-of-sample MSE {np.mean(list(e.values())):.4f} vs brain features {np.mean(list(e0.values())):.4f}")
os.makedirs("knowledge/research_out", exist_ok=True); open("knowledge/research_out/garch_vs_brain.txt", "w").write("\n".join(out)); print("\n".join(out))
