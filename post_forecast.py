"""Posts the newest Claude forecast (last row of predictions.csv) to the Discord channel.
Triggered by the 'forecast-post' workflow whenever predictions.csv changes."""
import json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qqq_gex_daily as q
import analyst

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs.json")
p = pd.read_csv(os.path.join(HERE, "predictions.csv"))
r = p.iloc[-1]
try:
    runs = json.load(open(RUNS))
except Exception:
    runs = {}
key = f"{r['date']}|{r.get('model', '')}"
if runs.get("forecast_posted") == key:
    print("already posted"); sys.exit(0)

p1, p5 = float(r["p_up_1d"]), float(r["p_up_5d"])
word = lambda x: "BULLISH" if x >= 0.58 else "BEARISH" if x <= 0.46 else "NEUTRAL"
late = str(r.get("model", "")).endswith("-late")
drivers = [d.strip() for d in str(r.get("drivers", "")).split("|") if d.strip() and d.strip() != "nan"]
body = ["EXPERIMENTAL - not a trade signal until the scorecard proves it." + (" LATE - not graded." if late else ""),
        f"Next session: **{word(p1)}** - P(up) {p1:.0%} (base rate {analyst.BASE_UP:.0%})",
        f"Next 5 sessions: {word(p5)} - P(up) {p5:.0%} - confidence: {r.get('confidence', '?')}", ""]
body += ["Why:"] + [f"- {d}" for d in drivers] + [""]
body += analyst.scorecard(os.path.join(HERE, "predictions.csv"), os.path.join(HERE, "qqq_closes.csv"))
q.push(f"Forecast for the session after {r['date']}: {word(p1)} {p1:.0%} (unproven)", "\n".join(body),
       priority="default", tags="crystal_ball")
runs["forecast_posted"] = key
json.dump(runs, open(RUNS, "w"))
