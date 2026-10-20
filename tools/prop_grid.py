import sys, time, warnings, json; warnings.filterwarnings("ignore"); sys.path.insert(0, "/home/claude/nasdaq-bot")
import numpy as np, pandas as pd, test_engine as T, strategy_lab as S, prop_sim as P
M, X = T.frame(); D = S.data(); sess = D["M"].session.values
rng = np.random.default_rng(42); X["rnd"] = rng.choice([-1.0, 1.0], len(X))
out = {}
t0 = time.time()
for side in ("long", "short", "rnd"):
    for stop in (10, 20, 40):
        for tr in (0.5, 1, 2):
            spec = {"kind": "strategy", "name": f"{side} {stop}/{tr}R", "entry": {"type": "time", "at": "08:31", "side": side},
                    "stop": {"points": stop}, "target": {"R": tr}, "exit": "14:55"}
            Tb = S.backtest(spec, X)
            pts = pd.Series(0.0, index=sess); pts[Tb.session.values] = Tb.pnl.values
            out[spec["name"]] = {"pts": pts.values.tolist(), "stop": stop, "avgR": round(float(Tb.R.mean()), 3), "n": len(Tb), "win": round(float((Tb.pnl > 0).mean()), 3)}
            print(spec["name"], out[spec["name"]]["n"], out[spec["name"]]["avgR"], out[spec["name"]]["win"], round(time.time() - t0)); sys.stdout.flush()
json.dump({"sessions": list(sess), "grid": out}, open("/home/claude/brain/prop_grid.json", "w"))
