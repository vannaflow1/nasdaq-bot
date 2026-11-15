"""tools/sim_inputs.py - publishes the ONE daily number an execution script on the owner's PC needs: the stop input.

Plain words: F10 and F13 place their stop at a fixed share (0.2) of the day's EXPECTED range, and that expected range is
the brain's evening forecast for the next session, exp(l_bot) (frozen in knowledge/frozen/F10_forward_inputs.json:
"A session without that forecast does not trade; it never falls back to a different stop rule"). A NinjaTrader script
cannot compute that forecast itself, so this writes it to knowledge/sim_inputs.json, a small public file the script
reads once before the session (ninjatrader/README.md).

It only copies a number Volta already produced (the newest row of brain_preds.csv). It changes no forecast, no frozen
file and no test. Run: python tools/sim_inputs.py   (the evening workflow runs it after the forecast is written)"""
import json, math, os, sys
from datetime import datetime, timezone
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.path.join(HERE, "brain_preds.csv"); OUT = os.path.join(HERE, "knowledge", "sim_inputs.json")


def latest(preds):
    """(session 'YYYY-MM-DD', fc_frac) from the newest forecast row that has an l_bot, or None."""
    for r in preds.sort_values("next_date").iloc[::-1].itertuples():
        try:
            lb = float(json.loads(r.feat)["l_bot"])
            if math.isfinite(lb): return str(r.next_date)[:10], math.exp(lb)
        except Exception:
            continue
    return None


def main():
    got = latest(pd.read_csv(PREDS)) if os.path.exists(PREDS) else None
    if not got:
        print("no forecast row with l_bot - nothing written (a script reading the old file will see an old date and not trade)"); return 1
    session, fc = got
    out = {"session": session, "fc_frac": round(fc, 6), "stop_share_of_range": 0.2,
           "made_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
           "how_to_use": "stop distance in points = stop_share_of_range x fc_frac x the 08:30 Chicago open, rounded to the tick, "
                         "at least 8 ticks. Use it ONLY when 'session' is today's date in Chicago; otherwise do not trade."}
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if {k: old.get(k) for k in ("session", "fc_frac")} == {"session": session, "fc_frac": out["fc_frac"]}:
        print("unchanged:", session, out["fc_frac"]); return 0
    json.dump(out, open(OUT, "w"), indent=1)
    print("written:", session, "fc_frac", out["fc_frac"]); return 0


if __name__ == "__main__":
    sys.exit(main())
