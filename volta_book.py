"""volta_book.py - Volta as a trader: its own virtual prop account.

Rules (like a 25K prop evaluation/funded account):
  - starts at $25,000; end-of-day trailing max loss $1,000 (floor = highest end-of-day balance - $1,000,
    locked at $25,100 once the balance has closed at $26,100+). Closing at or below the floor = account blown ->
    it is logged and Volta starts a new account (the count of blown accounts stays on its record forever)
  - risk per trade: 10% of the buffer to the floor, max $250; daily loss limit $500
  - Volta ONLY trades edges that passed its full protocol: strategies that passed the locked 2024-26 exam (traded
    with the exact backtest rules on the day's real 1-minute bars by strategy_forward.py) and the short-vol iron fly
    on high-gamma days (volflag.py, sized at 1% of the account per trade). Nothing else - no tested edge, no trade.
Every evening (after strategy_forward + volflag --grade): books the day's trades, writes the journal, updates the
account and the /book status. Every trade and every 'no trade' day is journaled with the reason."""
import json, math, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); B = os.path.join(K, "book")
sys.path.insert(0, HERE)
CT = ZoneInfo("America/Chicago")
ACCT, TRADES, JOURNAL, STATUS = (os.path.join(B, "account.json"), os.path.join(B, "trades.csv"), os.path.join(B, "journal.jsonl"),
                                 os.path.join(HERE, "status.json"))
START, MLL, LOCK_AT, LOCK_FLOOR, RISK_CAP, DAY_LIMIT, MNQ = 25_000.0, 1_000.0, 26_100.0, 25_100.0, 250.0, 500.0, 2.0
HOOK = os.environ.get("DISCORD_WEBHOOK_LEARN") or os.environ.get("DISCORD_WEBHOOK") or None


def new_account(n=1, blown=0, today=None):
    return {"account": n, "opened": today or str(datetime.now(CT).date()), "balance": START, "peak_eod": START,
            "floor": START - MLL, "blown": blown, "trades": 0, "booked": [], "last_day": None}


def load():
    os.makedirs(B, exist_ok=True)
    return json.load(open(ACCT)) if os.path.exists(ACCT) else new_account()


def risk_budget(a):
    return max(0.0, min(RISK_CAP, 0.10 * (a["balance"] - a["floor"])))


def journal(entry):
    with open(JOURNAL, "a") as f: f.write(json.dumps(entry) + "\n")


def todays_trades(a, today):
    """Collect today's finished trades from the tested edges that Volta hasn't booked yet."""
    out = []
    # 1. strategies that passed the locked exam, traded on today's real bars
    f = os.path.join(K, "strategy_forward.csv")
    if os.path.exists(f):
        F = pd.read_csv(f)
        for _, r in F[(F.date.astype(str) == today) & (F.traded == True)].iterrows():
            key = f"strat:{today}:{r.id}"
            if key in a["booked"]: continue
            stop = abs(float(r.pnl_pts) / float(r.R)) if float(r.R) else None
            out.append({"key": key, "edge": f"strategy: {r['name']}", "side": "LONG" if r.side > 0 else "SHORT",
                        "pts": float(r.pnl_pts), "R": float(r.R), "stop_pts": stop, "kind": "futures",
                        "why": "passed the locked 2024-26 exam, traded with the exact backtest rules"})
    # 2. short-vol iron fly on high-gamma days (settles at expiry)
    f = os.path.join(K, "paper_vol.csv")
    if os.path.exists(f):
        L = pd.read_csv(f)
        for _, r in L[L.status == "closed"].iterrows():
            key = f"vol:{r.date}:{r.expiry}"
            if key in a["booked"]: continue
            out.append({"key": key, "edge": f"short-vol iron fly {r.kp:g}/{r.K:g}/{r.kc:g} (opened {r.date}, expired {r.expiry})",
                        "side": "SHORT VOL", "pnl_per_lot": float(r.pnl) * 100, "maxloss_per_lot": float(r.maxloss) * 100,
                        "kind": "options", "why": f"dealer gamma rank {float(r['rank']):.2f} > 0.7 - tested edge (straddle t 5.3, fly t 3.3)"})
    return out


def book(a, t, day_pnl):
    if t["kind"] == "futures":
        if not t["stop_pts"]:
            n = max(1, int(risk_budget(a) // (15 * MNQ)))
        else:
            n = int(risk_budget(a) // (t["stop_pts"] * MNQ))
        n = min(n, 20)
        if n == 0:
            return None, "skipped: stop too wide for my risk budget (even 1 MNQ risks more than 10% of my buffer)"
        usd = round(n * t["pts"] * MNQ, 2); size = f"{n} MNQ"
    else:
        ml = max(t["maxloss_per_lot"], 1.0); buffer = a["balance"] - a["floor"]
        lots = int((0.01 * a["balance"]) // ml)                     # 1% of the account at risk (the tested sizing)
        if lots == 0 and ml <= 0.02 * a["balance"]: lots = 1        # one lot allowed up to 2%
        lots = min(lots, int((0.3 * buffer) // ml))                 # never more than 30% of the buffer on one fly
        if lots == 0:
            return None, f"skipped: one fly risks ${ml:,.0f}, too much for my account/buffer"
        usd = round(lots * t["pnl_per_lot"], 2); size = f"{lots} lot{'s' if lots > 1 else ''}"
    if day_pnl <= -DAY_LIMIT:
        return None, "skipped: daily loss limit already hit"
    return {"usd": usd, "size": size}, None


def write_status(a, today_lines):
    T = pd.read_csv(TRADES) if os.path.exists(TRADES) else pd.DataFrame()
    cur = T[T.account == a["account"]] if len(T) else T
    lines = [f"VOLTA'S BOOK - account #{a['account']} (since {a['opened']}){' | blown accounts so far: ' + str(a['blown']) if a['blown'] else ''}",
             f"Balance ${a['balance']:,.2f} ({a['balance'] - START:+,.2f}) | max-loss floor ${a['floor']:,.0f} | buffer ${a['balance'] - a['floor']:,.0f}",
             f"Trades: {len(cur)}" + (f", win {(cur.usd > 0).mean():.0%}, best ${cur.usd.max():+,.0f}, worst ${cur.usd.min():+,.0f}" if len(cur) else " - waiting for a tested edge to trigger"),
             f"Next trade risks up to ${risk_budget(a):,.0f}."]
    if today_lines: lines += ["", "LATEST:"] + today_lines
    lines += ["", "Volta only trades edges that passed its full protocol (walk-forward, placebo, stress test, locked exam).",
              "Virtual money - this is Volta's live track record, not advice."]
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    st["book"] = lines; json.dump(st, open(STATUS, "w"), indent=1)
    return lines


def armed_line():
    """One line for the morning plan: what Volta may trade today."""
    a = load(); armed = ["short-vol fly if dealer gamma rank > 0.7 at 15:20 NY"]
    try:
        import strategy_forward as SF
        armed += [c["name"][:60] for c in SF.candidates(SF.entries())]
    except Exception:
        pass
    return f"VOLTA'S BOOK: ${a['balance']:,.0f} (buffer ${a['balance'] - a['floor']:,.0f}) - armed today: " + "; ".join(armed)


def main():
    now = datetime.now(CT); today = str(now.date())
    a = load()
    trades = todays_trades(a, today)
    day_pnl, lines = 0.0, []
    for t in trades:
        res, why_not = book(a, t, day_pnl)
        a["booked"].append(t["key"]); a["booked"] = a["booked"][-400:]
        if not res:
            journal({"date": today, "account": a["account"], "edge": t["edge"], "decision": why_not}); lines.append(f"- {t['edge']}: {why_not}"); continue
        a["balance"] = round(a["balance"] + res["usd"], 2); a["trades"] += 1; day_pnl += res["usd"]
        row = {"date": today, "account": a["account"], "edge": t["edge"], "side": t["side"], "size": res["size"], "usd": res["usd"],
               "R": t.get("R"), "balance": a["balance"]}
        T = pd.read_csv(TRADES) if os.path.exists(TRADES) else pd.DataFrame()
        pd.concat([T, pd.DataFrame([row])], ignore_index=True).to_csv(TRADES, index=False)
        verdict = "WIN" if res["usd"] > 0 else "LOSS" if res["usd"] < 0 else "SCRATCH"
        journal({**row, "why": t["why"], "result": verdict})
        lines.append(f"- {verdict} {res['usd']:+,.2f} | {t['side']} {res['size']} | {t['edge']} | why: {t['why']}")
    if now.weekday() < 5 and a.get("last_day") != today:
        a["last_day"] = today
        if not trades:
            journal({"date": today, "account": a["account"], "decision": "no trade - none of my tested edges triggered today"})
        # end-of-day trailing max loss
        a["peak_eod"] = max(a["peak_eod"], a["balance"])
        a["floor"] = LOCK_FLOOR if a["peak_eod"] >= LOCK_AT else max(a["floor"], a["peak_eod"] - MLL)
        if a["balance"] <= a["floor"]:
            journal({"date": today, "account": a["account"], "decision": f"ACCOUNT BLOWN at ${a['balance']:,.2f} (floor ${a['floor']:,.0f}) - starting a new one"})
            lines.append(f"ACCOUNT #{a['account']} BLOWN at ${a['balance']:,.2f}. Starting account #{a['account'] + 1}.")
            a = {**new_account(a["account"] + 1, a["blown"] + 1, today), "booked": a["booked"], "last_day": today}
    json.dump(a, open(ACCT, "w"), indent=1)
    L = write_status(a, lines)
    print("\n".join(L))
    if lines and HOOK and "--dry" not in sys.argv:
        import qqq_gex_daily as q
        q.push(f"📒 Volta's book - ${a['balance']:,.2f}", "\n".join(lines + ["", L[1]]), tags="ledger", hook=HOOK)


if __name__ == "__main__":
    main()
