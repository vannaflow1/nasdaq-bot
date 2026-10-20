import sys, json, numpy as np, pandas as pd; sys.path.insert(0, "/home/claude/nasdaq-bot")
import prop_sim as P
G = json.load(open("/home/claude/brain/prop_grid.json")); sess = pd.to_datetime(G["sessions"])
early = [i for i in range(0, len(sess) - 60, 3) if sess[i].year <= 2021]; late = [i for i in range(0, len(sess) - 60, 3) if sess[i].year >= 2022]
rows = []
for name, g in G["grid"].items():
    pts = np.array(g["pts"]); worst = np.where(pts != 0, -float(g["stop"]), 0.0)
    for n in (1, 2, 3, 5, 8, 12):
        def size(phase, profit, buf, n=n, st=g["stop"]): return min(n, int((buf - 1) // (st * P.MNQ)))
        for plan in ("flex25", "pro25"):
            a = P.evaluate(pts, worst, plan, size, starts=early); b = P.evaluate(pts, worst, plan, size, starts=late)
            rows.append({"shape": name, "avgR": g["avgR"], "win": g["win"], "mnq": n, "plan": plan,
                         "pass_14_21": a["pass_rate"], "payout_14_21": a["avg_payout_per_eval"], "pass_22_26": b["pass_rate"], "payout_22_26": b["avg_payout_per_eval"],
                         "live_22_26": b["reach_live"], "days_22_26": b["median_days"]})
R = pd.DataFrame(rows); R.to_csv("/home/claude/brain/prop_eval.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 80)
print(R.sort_values("payout_14_21", ascending=False).head(25).to_string(index=False))
print("\nzero-edge (random side) best:"); print(R[R.shape.str.startswith("rnd")].sort_values("payout_14_21", ascending=False).head(8).to_string(index=False))
