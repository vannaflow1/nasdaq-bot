"""volflag.py - paper-trades the one options edge Volta found in testing (see knowledge: straddle-gamma):
on HIGH-gamma days (gamma rank > 0.7 vs the last 252 days) sell the nearest-expiry ATM QQQ straddle and buy
wings 2x the straddle price away (an iron fly with capped risk). Backtest 2017-2025: +8.1 bp of QQQ per trade,
t 3.3, 58% wins. This is a PAPER trade log to see whether it holds live - nothing is traded.

  python volflag.py          ~15:35 NY: decide, post the trade to #options if it is a short-vol day, log it
  python volflag.py --grade  after the close: settle open paper trades whose expiry has passed
  python volflag.py --dry    print the decision only, write nothing
"""
import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import qqq_gex_daily as q
import brain

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "paper_vol.csv")
STATUS = os.path.join(HERE, "status.json")
HOOK = os.environ.get("DISCORD_WEBHOOK_NERD") or None
THRESH, WING = 0.7, 2.0
NY = ZoneInfo("America/New_York")
COLS = ["date", "expiry", "S", "K", "kp", "kc", "credit", "maxloss", "rank", "status", "S_T", "pnl", "pnl_bp"]


def load_log():
    return pd.read_csv(LOG, dtype={"date": str, "expiry": str}) if os.path.exists(LOG) else pd.DataFrame(columns=COLS)


def gamma_rank(gexn):
    h = pd.read_csv(q.HIST).sort_values("date")
    prev = h.gexn.astype(float).tail(252).to_numpy()
    return float((gexn > prev).mean()), int((h.date >= "2026-01-01").sum())


def pick(d, S, today):
    exp = d.loc[d.expiration > today, "expiration"].min()
    x = d[(d.expiration == exp) & (d.bid > 0) & (d.ask > 0)]
    K = float(x.strike.iloc[(x.strike - S).abs().argmin()])
    c = x[x.is_call & (x.strike == K)].iloc[0]; p = x[~x.is_call & (x.strike == K)].iloc[0]
    mid = (c.bid + c.ask + p.bid + p.ask) / 2; w = WING * mid
    cw = x[x.is_call & (x.strike >= K + w)].sort_values("strike").iloc[0]
    pw = x[~x.is_call & (x.strike <= K - w)].sort_values("strike").iloc[-1]
    credit = c.bid + p.bid - cw.ask - pw.ask
    maxloss = max(cw.strike - K, K - pw.strike) - credit
    return dict(expiry=f"{exp:%Y-%m-%d}", K=K, kc=float(cw.strike), kp=float(pw.strike), credit=round(float(credit), 2),
                maxloss=round(float(maxloss), 2), straddle_bid=round(float(c.bid + p.bid), 2), straddle_mid=round(float(mid), 2))


def scorecard(L):
    done = L[L.status == "closed"]
    if done.empty:
        return "Live paper score: no closed trades yet (backtest: +8.1 bp/trade, 58% wins)."
    return (f"Live paper score: {len(done)} trades, {(done.pnl > 0).mean():.0%} wins, avg {done.pnl_bp.mean():+.1f} bp of QQQ, "
            f"total ${100 * done.pnl.sum():+,.0f} per 1-lot  (backtest: +8.1 bp/trade, 58% wins)")


def write_status(lines):
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    st["shortvol"] = lines
    json.dump(st, open(STATUS, "w"), indent=1)


def decide(dry=False):
    now = datetime.now(NY)
    if not dry and "--force" not in sys.argv and not ("15:20" <= f"{now:%H:%M}" <= "15:59"):
        print(f"{now:%H:%M} NY is outside the 15:20-15:59 window - skip"); return
    today = pd.Timestamp(now.date())
    L = load_log()
    if not dry and (L.date == f"{today:%Y-%m-%d}").any():
        print("already decided today"); return
    ts, d = q.load_chain(None)
    live = d[(d.dte >= 0) & (d.dte <= 45) & (d.bid > 0) & (d.ask > 0)]
    if len(live) < 200:
        print("market closed - no decision"); return
    S = q.spot_by_parity(d); g = q.gexn(d, S); rank, live_days = gamma_rank(g)
    head = f"SHORT-VOL CHECK {now:%a %d %b %H:%M} NY - QQQ {S:.2f}, gamma rank {rank:.2f} (needs > {THRESH})"
    basis = f"(rank vs last 252 readings; {live_days} of them live from 2026 - it gets sharper as live history builds)"
    if rank <= THRESH:
        lines = [head, "Not a short-vol day: no paper trade.", basis, "", scorecard(L)]
        print("\n".join(lines))
        if not dry:
            write_status(lines)
        return
    t = pick(d, S, today)
    bp = t["credit"] / S * 1e4
    lines = [f"PAPER TRADE - short-vol day (gamma rank {rank:.2f})",
             f"Iron fly on QQQ, expiry {t['expiry']}:",
             f"  sell {t['K']:g} call + {t['K']:g} put (straddle bid {t['straddle_bid']:.2f})",
             f"  buy {t['kc']:g} call + {t['kp']:g} put (wings 2x the straddle away)",
             f"  credit {t['credit']:.2f} (${100 * t['credit']:,.0f} per 1-lot), max loss {t['maxloss']:.2f} (${100 * t['maxloss']:,.0f})",
             f"  breakevens {t['K'] - t['credit']:.2f} / {t['K'] + t['credit']:.2f}, held to expiry",
             "Why: on high-gamma days dealer hedging damps moves, but options still price a normal day. "
             "Backtest 2017-2025: +8.1 bp of QQQ per trade, t 3.3, 58% wins, worst -2.1%.",
             "Paper trade only, to check the edge live. Prices ~15 min delayed. Not financial advice.",
             basis, "", scorecard(L)]
    print("\n".join(lines))
    if dry:
        return
    row = dict(date=f"{today:%Y-%m-%d}", expiry=t["expiry"], S=round(S, 2), K=t["K"], kp=t["kp"], kc=t["kc"],
               credit=t["credit"], maxloss=t["maxloss"], rank=round(rank, 3), status="open", S_T="", pnl="", pnl_bp="")
    pd.concat([L, pd.DataFrame([row])], ignore_index=True)[COLS].to_csv(LOG, index=False)
    write_status(lines)
    q.push("Short-vol day (paper trade)", "\n".join(lines), tags="nerd", hook=HOOK)


def grade():
    L = load_log()
    op = L[L.status == "open"]
    if op.empty:
        print("nothing to grade"); return
    c = brain.yahoo("QQQ", "1mo").close
    msgs = []
    for i, r in op.iterrows():
        e = pd.Timestamp(r.expiry)
        if e not in c.index:
            continue                                   # expiry close not in yet
        ST = float(c.loc[e]); K, kc, kp = float(r.K), float(r.kc), float(r.kp)
        payoff = abs(ST - K) - max(ST - kc, 0) - max(kp - ST, 0)
        pnl = float(r.credit) - payoff
        L.loc[i, ["status", "S_T", "pnl", "pnl_bp"]] = ["closed", round(ST, 2), round(pnl, 2), round(pnl / float(r.S) * 1e4, 1)]
        msgs.append(f"{r.date} iron fly {kp:g}/{K:g}/{kc:g} exp {r.expiry}: QQQ closed {ST:.2f} -> "
                    f"{'WIN' if pnl > 0 else 'LOSS'} {pnl:+.2f} (${100 * pnl:+,.0f} per 1-lot)")
    if not msgs:
        print("no expiries settled yet"); return
    L[COLS].to_csv(LOG, index=False)
    body = "\n".join(msgs + ["", scorecard(L)])
    print(body)
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    write_status((st.get("shortvol") or [])[:1] + ["", "LAST GRADED:"] + msgs + ["", scorecard(L)])
    q.push("Short-vol paper trade graded", body, tags="nerd", hook=HOOK)


if __name__ == "__main__":
    if "--grade" in sys.argv:
        grade()
    else:
        decide(dry="--dry" in sys.argv)
