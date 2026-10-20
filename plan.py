"""plan.py - the daily trading plan, posted to #briefings ~10 minutes before the NY open (inside the session loop, once a
day). It doesn't pick trades. It sets SIZE and LOSS LIMITS for a prop account from what Volta knows about today:
expected move, risk level, gamma, events. Tested facts behind it:
 - after touching a level, NQ runs through it within 30 min by a median 0.26x the day's expected move (16,900 touches 2014-2026);
   a stop survives that overshoot: 0.06x -> 12%, 0.10x -> 20%, 0.20x -> 40%, 0.30x -> 57%, 0.40x -> 70% of touches
 - low gamma / events / tail days = bigger moves (validated); the plan halves size on those days
/plan in Discord gives the same plan for YOUR buffer (distance to the max-loss limit) and stop."""
import json, math, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CT = ZoneInfo("America/Chicago")
STATUS, STATE = os.path.join(HERE, "status.json"), os.path.join(HERE, "knowledge", "plan_state.json")
SURV = [(0.025, .05), (0.04, .08), (0.06, .12), (0.08, .16), (0.10, .20), (0.15, .30), (0.20, .40), (0.30, .57), (0.40, .70)]


def survive(stop, move):
    r = stop / move; prev = (0.0, 0.0)
    for x, p in SURV:
        if r <= x: return prev[1] + (p - prev[1]) * (r - prev[0]) / (x - prev[0])
        prev = (x, p)
    return 0.75


def plan_data(st):
    bp = st.get("brain_pred") or {}
    feat = {}
    try:
        import csv
        rows = [r for r in csv.DictReader(open(os.path.join(HERE, "brain_preds.csv"))) if r.get("next_date", "")[:10] == bp.get("date")]
        if rows: feat = json.loads(rows[-1]["feat"])
    except Exception:
        pass
    nq = float(bp.get("nq") or 0)
    move = math.exp(float(feat["l_bot"])) * nq if "l_bot" in feat and nq else None
    if move and bp.get("spx_factor"): move *= float(bp["spx_factor"])          # SPX dealer check (spx_morning.py)
    level = st.get("level") or "NORMAL"; g = bp.get("gex_rank")
    mult, why = 1.0, []
    if level in ("ELEVATED", "HIGH"): mult = 0.5; why.append(f"risk level {level}")
    if g is not None and g < 0.2 and mult > 0.5: mult = 0.5; why.append("very low dealer gamma (bigger, faster moves)")
    ev = level == "HIGH"
    return {"date": bp.get("date"), "move": round(move) if move else None, "range": round(float(bp.get("pred", 0)) * nq) if nq else None,
            "level": level, "mult": mult, "why": why or ["normal conditions"], "event_day": ev}


def lines_for(d, buffer=None, stop=None, micro=True):
    if not d.get("move"): return ["No plan today (no forecast for this session)."]
    mv = d["move"]; pt = 2.0 if micro else 20.0; name = "MNQ" if micro else "NQ"
    out = [f"TRADING PLAN - {d['date']}  |  expected move ±{mv} pts, full-day range ~{d['range']} pts, risk {d['level']}",
           f"Size factor today: {d['mult']:.0%}  ({'; '.join(d['why'])})"]
    if d.get("event_day"): out.append("Event day: be flat into the release and skip the first 15 minutes after it.")
    out += ["", "STOPS on a day like this (share of level touches where price did NOT run past the stop within 30 min):"]
    for s in sorted({15, 25, 40, 60, round(0.2 * mv), round(0.3 * mv)}):
        out.append(f"  {s:>4} pt stop -> survives ~{survive(s, mv):.0%} of touches")
    out.append(f"  Median overshoot through a level today: ~{round(0.26 * mv)} pts.")
    if buffer:
        risk = buffer * 0.10 * d["mult"]
        out += ["", f"YOUR NUMBERS (buffer ${buffer:,.0f} to the max-loss limit):",
                f"  Max risk per trade: ${risk:,.0f}  (10% of buffer x size factor - survives 10 straight losses)",
                f"  Daily stop: ${2 * risk:,.0f}  (2 losses and done)"]
        for s in ([stop] if stop else [15, 40, round(0.2 * mv)]):
            n = int(risk // (s * pt)) if s else 0
            out.append(f"  {s} pt stop -> {n} {name}" + ("  (too small - skip or use micros)" if n == 0 else "")
                       + f"  | ~1 in {1 / max(survive(s, mv), .01):.0f} level touches doesn't run past this stop")
    else:
        out += ["", "SIZE PER $1,000 OF BUFFER (distance to your max-loss limit):",
                f"  risk per trade ${100 * d['mult']:.0f}, daily stop ${200 * d['mult']:.0f}",
                f"  -> 15 pt stop: {int(100 * d['mult'] // 30)} MNQ  |  40 pt stop: {int(100 * d['mult'] // 80)} MNQ  |  {round(0.2 * mv)} pt stop: {int(100 * d['mult'] // (0.4 * mv))} MNQ"]
    out += ["", "Lucid rules to respect: EOD trailing max loss; 40% consistency (no single day > 40% of the cycle's profit).",
            "Use /plan buffer:<$> stop:<pts> for your exact numbers. Sizing guidance, not trade signals or financial advice."]
    return out


def main():
    now = datetime.now(CT); m = now.hour * 60 + now.minute
    if now.weekday() >= 5 or not (8 * 60 <= m < 8 * 60 + 30) and "--force" not in sys.argv: return
    s = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if s.get("date") == str(now.date()) and "--force" not in sys.argv: return
    try:                                                      # SPX dealer gamma + walls adjust today's range first
        import spx_morning
        spx_morning.adjust()
    except Exception as e:
        print("spx morning check skipped:", type(e).__name__, str(e)[:120])
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    d = plan_data(st); L = lines_for(d)
    if st.get("spx_morning") and (st.get("brain_pred") or {}).get("spx_factor"):
        L.insert(2, st["spx_morning"][0])
    try:
        import volta_book
        L.append(""); L.append(volta_book.armed_line())
    except Exception as e:
        print("book line skipped:", e)
    st["plan"] = L; st["plan_data"] = d; json.dump(st, open(STATUS, "w"), indent=1)
    json.dump({"date": str(now.date())}, open(STATE, "w"))
    print("\n".join(L))
    hook = os.environ.get("DISCORD_WEBHOOK")
    if hook and "--dry" not in sys.argv:
        import qqq_gex_daily as q
        q.push(f"📋 Trading plan - risk {d['level']}, size {d['mult']:.0%}", "\n".join(L[1:]), tags="clipboard", hook=hook)


if __name__ == "__main__":
    main()
