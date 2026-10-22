"""tools/null_rescore.py - every family ever scored, re-tested with null v3 (22 Oct 2026). Append-only record.

Why: the family test's placebo drew independent coin flips per variant and took the median over ~50 variants. The
variants are near-copies of one signal, so that null was 3-4x too narrow and every p-value too small. Null v3 shares one
random draw per market-session across all variants (families.null_draws). The original rows in families_ledger.csv are
NOT rewritten (their frozen commit, p and alpha are hash-chained): this file records, next to them, what each family's
p-value is under null v3 on exactly the same trades and window, at the alpha it was originally tested at.
Output: knowledge/ledgers/null_v3_rescore.json. Run once: python tools/null_rescore.py"""
import json, os, sys, time
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "knowledge", "ledgers", "null_v3_rescore.json")


def main():
    import strategy_lab as S, test_engine as TE, families as FA
    _, X = TE.frame(); L = FA.ledger(); F = {f["id"]: f for f in json.load(open(FA.REG))}
    out = {"date": datetime.now(timezone.utc).date().isoformat(), "method": "null v3: one shared draw per market-session, "
           f"{FA.NULL_REPS} draws, exact randomization p; same trades and window as the original test", "families": []}
    for r in L.itertuples():
        fam = F.get(r.family)
        if fam is None: continue
        t0 = time.time()
        res, _, _ = FA.score_family(fam, X, S)
        if "p" not in res: out["families"].append({"family": r.family, "note": res.get("verdict")}); continue
        alpha = float(r.alpha); share = res.get("share_positive_B"); p = res["p"]
        med = res["median_contrast"] if fam.get("statistic") == "contrast" else res.get("median_edge_B")   # contrast: low minus high
        old_pass = bool(r.passed) if isinstance(r.passed, (bool, np.bool_)) else str(r.passed) == "True"
        new_pass = bool(med is not None and med > 0 and share >= 0.6 and p < alpha)
        row = {"family": r.family, "name": r.name, "alpha": alpha, "p_original": float(r.p), "p_null_v3": p,
               "median_edge": med, "share_positive": share, "no_info_level": res.get("placebo_median_mean"),
               "passed_original": old_pass, "passed_null_v3": new_pass,
               "change": "VOID - passed only because of the too-narrow null" if (old_pass and not new_pass) else
                         ("unchanged" if old_pass == new_pass else "would now pass")}
        out["families"].append(row); print(json.dumps(row), f"({time.time() - t0:.0f}s)", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT): raise SystemExit(f"{OUT} exists - this record is written once")
    json.dump(out, open(OUT, "w"), indent=1, default=float); print("written", OUT)


if __name__ == "__main__":
    main()
