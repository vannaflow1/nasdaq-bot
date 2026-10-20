import sys, json, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0, "/home/claude/nasdaq-bot")
import numpy as np, test_engine as T, strategy_lab as S
M, X = T.frame(); D = S.data(); ins = np.where(D["M"].session < S.EXAM_FROM)[0]
L = [json.loads(l) for l in open(S.LOG) if l.strip()]
for e in L:
    if e.get("prop"): continue
    try:
        Tb = S.backtest(e["spec"], X, ins)
        if len(Tb) >= 50:
            e["prop"] = S.prop_score(Tb, D["M"], e["spec"]); print(f"{e['prop'][0]['ev_per_eval']:+7.1f} {e['prop'][0]['plan']:15s} {e['name'][:60]}"); sys.stdout.flush()
    except Exception as ex:
        print("skip", e.get("name"), ex)
open(S.LOG, "w").write("".join(json.dumps(e) + "\n" for e in L))
