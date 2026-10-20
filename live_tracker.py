"""
live_tracker.py - Volta during the US session (runs every 5 min, standard library only).
Watches NQ (free delayed data) against the brain's forecast and posts tested alerts:
  * 10:00 NY mid-morning update: the brain's range forecast re-estimated from what already happened
    (walk-forward 2019-2025: 16% smaller miss at 10:00 NY, 46% at 13:00 NY; 80% bands held 80%)
  * expected range used up (100% / 130%): how much more the rest of the session usually adds
  * far high / far low hit: only ~10% of days get there; what usually happens next
"""
import json, math, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS, STATE = os.path.join(HERE, "status.json"), os.path.join(HERE, "live_state.json")
IM = json.load(open(os.path.join(HERE, "models", "intraday_model.json")))
FAR = json.load(open(os.path.join(HERE, "models", "farlevel_stats.json")))
NNP = os.path.join(HERE, "models", "intraday_nn.json")
NN = json.load(open(NNP)) if os.path.exists(NNP) else None
VOLH = os.path.join(HERE, "live_volhist.json")
PWP = os.path.join(HERE, "models", "powers.json")
PW = json.load(open(PWP)) if os.path.exists(PWP) else None
HOOK = os.environ.get("DISCORD_WEBHOOK_LIVE") or os.environ.get("DISCORD_WEBHOOK", "")
CT, NY, LUX = ZoneInfo("America/Chicago"), ZoneInfo("America/New_York"), ZoneInfo("Europe/Luxembourg")
DRY = "--dry" in sys.argv


def push(title, body, color=0x1C7ED6):
    if DRY or not HOOK:
        print("[would post]", title, "\n" + body); return
    data = json.dumps({"username": "Volta", "embeds": [{"title": title[:256], "description": body[:4000], "color": color}],
                       "allowed_mentions": {"parse": []}}).encode()
    req = urllib.request.Request(HOOK, data=data, method="POST", headers={"Content-Type": "application/json",
                                                                           "User-Agent": "DiscordBot (Volta, 1.0)"})
    for a in range(3):
        try:
            urllib.request.urlopen(req, timeout=30).read(); return
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 + 2 * a); continue
            print("push failed", e); return
        except Exception as e:
            print("push failed", e); return


def bars():
    u = "https://query1.finance.yahoo.com/v8/finance/chart/NQ%3DF?interval=1m&range=5d&includePrePost=true"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    r = r["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(r["timestamp"]):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None not in (o, h, l, c):
            out.append((datetime.fromtimestamp(t, timezone.utc).astimezone(CT), o, h, l, c, (q.get("volume") or [0] * (i + 1))[i] or 0))
    return out


def nn_logrange(B, o, so, pred, chk, bp, volh):
    """Neural net (5 small MLPs, trained 2014-2025 on 1-minute NQ) - same inputs as in training."""
    C = [b[4] for b in B]; H = [b[2] for b in B]; Lw = [b[3] for b in B]; V = [b[5] for b in B]
    lr = [math.log(C[0] / o)] + [math.log(C[i] / C[i - 1]) for i in range(1, len(C))]
    sd = lambda x: math.sqrt(sum((v - sum(x) / len(x)) ** 2 for v in x) / len(x))
    w = slice(max(0, len(C) - 30), len(C)); hi, lo = max(H), min(Lw)
    lg = lambda x: math.log(max(x, 1e-6))
    def rel(key, cur):
        h = volh.get(key, [])[-20:]
        return lg(cur / (sum(h) / len(h))) if len(h) >= 5 and sum(h) > 0 and cur > 0 else None
    f = {"lp": lg(pred), "lso": lg(so), "lr30": lg((max(H[w]) - min(Lw[w])) / o), "lrv30": lg(sd(lr[w])), "lrvs": lg(sd(lr)),
         "mv": abs(C[-1] - o) / o * 100, "pos": (C[-1] - lo) / max(hi - lo, 1e-9),
         "lvol": rel(chk, sum(V)), "lvol30": rel(chk + "_30", sum(V[w])),
         "gex": bp.get("gex_rank"), "ev": None if bp.get("event_prem") is None else min(max(float(bp["event_prem"]), 0), 4)}
    names = list(IM)
    for j in range(15): f[f"c{j}"] = 1.0 if names[j] == chk else 0.0
    z = []
    for k, m, sc in zip(NN["features"], NN["mean"], NN["scale"]):
        v = f.get(k); z.append(0.0 if v is None else (v - m) / sc)        # missing input -> its average
    outs = []
    for net in NN["nets"]:
        a = z
        for i, (W, b) in enumerate(zip(net["W"], net["b"])):
            a = [sum(a[k] * W[k][j] for k in range(len(a))) + b[j] for j in range(len(b))]
            if i < len(net["W"]) - 1: a = [max(0.0, v) for v in a]
        outs.append(a[0])
    return sum(outs) / len(outs), (sum(V), sum(V[w]))


def _prob(m, f):
    z = m["intercept"]
    for k, mu, sc, c in zip(m["features"], m["mean"], m["scale"], m["coef"]):
        v = f.get(k); z += 0.0 if v is None else c * (v - mu) / sc
    return 1 / (1 + math.exp(-z))


RAW = {}


def open_read(allbars, sess, start):
    """The new powers, computed once at the NY open from overnight + yesterday (all known at 08:30 CT)."""
    if not PW: return None
    mins = lambda b: b[0].hour * 60 + b[0].minute
    prev_day = max((b[0].date() for b in allbars if b[0].date() < sess and 510 <= mins(b) < 900), default=None)
    P = [b for b in allbars if b[0].date() == prev_day and 510 <= mins(b) < 900]
    G = [b for b in allbars if start <= b[0] and (b[0].date() < sess or mins(b) < 510)]          # overnight 17:00 -> 08:30
    NY = [b for b in allbars if b[0].date() == sess and mins(b) >= 510]
    if not P or len(G) < 200 or not NY: return None
    ph, pl, pc = max(b[2] for b in P), min(b[3] for b in P), P[-1][4]
    o = NY[0][1]; oh, ol = max(b[2] for b in G), min(b[3] for b in G)
    asia = [b for b in G if mins(b) >= 1080 or mins(b) < 120]; lon = [b for b in G if 120 <= mins(b) < 420]
    pre = [b for b in G if 120 <= mins(b) < 510]
    feat = {}
    try:
        import csv
        rows = list(csv.DictReader(open(os.path.join(HERE, "brain_preds.csv"))))
        r = [x for x in rows if x.get("next_date", "")[:10] == str(sess)]
        if r: feat = json.loads(r[-1]["feat"])
    except Exception as e:
        print("powers: no evening features", e)
    if not feat: return None
    gap = (o - pc) / pc * 100
    feat.update(gap=gap, abs_gap=abs(gap), on_rel=math.log(max((oh - ol) / o, 1e-6)) - float(feat.get("l_rng20", -4.0)),
                on_pos=(o - ol) / max(oh - ol, 1e-9), open_vs_pdr=min(max((o - pl) / max(ph - pl, 1e-9), -2), 3))
    pct = lambda p: f"{p * 100:.0f}%"
    RAW.clear(); RAW.update(date=str(sess), pw_takes_pdh=round(_prob(PW["takes_pdh"], feat), 4), pw_takes_pdl=round(_prob(PW["takes_pdl"], feat), 4),
                            pw_gap_fill=round(_prob(PW["gap_fill"], feat), 4), pw_tail_day=round(_prob(PW["tail_day"], feat), 4))
    L = [f"OPEN READ - {sess:%a %d %b} (NY open {o:,.0f})"]
    if pl < o < ph:
        L.append(f"Yesterday's high {ph:,.0f}: {pct(_prob(PW['takes_pdh'], feat))} chance it gets taken today (avg {pct(PW['takes_pdh']['base'])})")
        L.append(f"Yesterday's low  {pl:,.0f}: {pct(_prob(PW['takes_pdl'], feat))} chance it gets taken today (avg {pct(PW['takes_pdl']['base'])})")
    else:
        L.append(f"Opened {'ABOVE yesterday high' if o >= ph else 'BELOW yesterday low'} ({ph:,.0f} / {pl:,.0f}) - already outside yesterday's range")
    if abs(gap) >= 0.2:
        L.append(f"Gap {gap:+.2f}% from yesterday's close {pc:,.0f}: {pct(_prob(PW['gap_fill'], feat))} chance it fills today (avg {pct(PW['gap_fill']['base'])})")
    else:
        L.append(f"No real gap ({gap:+.2f}%)")
    tp = _prob(PW["tail_day"], feat)
    L.append(f"Tail-day risk (range 1.8x+ its normal): {pct(tp)} (avg {pct(PW['tail_day']['base'])})" + ("  <- HIGH, size down" if tp > 0.18 else ""))
    if asia and lon:
        ah, al = max(b[2] for b in asia), min(b[3] for b in asia); lh, ll = max(b[2] for b in lon), min(b[3] for b in lon)
        sh = any(b[2] > ah for b in pre); sl = any(b[3] < al for b in pre); a = PW["asia"]
        L.append(f"Asia {al:,.0f}-{ah:,.0f} | London {ll:,.0f}-{lh:,.0f}")
        if sh and not sl:
            L.append(f"London already took the Asia HIGH -> NY takes the Asia LOW {pct(a['lon_swept_h_ny_takes_l'])} of the time (coin flip, no edge)")
        elif sl and not sh:
            L.append(f"London already took the Asia LOW -> NY takes the Asia HIGH {pct(a['lon_swept_l_ny_takes_h'])} of the time (coin flip, no edge)")
        elif sh and sl:
            L.append("London already took BOTH sides of Asia before the NY open")
        elif not sh and not sl:
            L.append(f"Asia range intact: NY takes the Asia high {pct(a['intact_take_h'])} / low {pct(a['intact_take_l'])}; "
                     f"once one side goes, the other follows only ~{pct(a['after_h_first_take_l'])}")
        L.append(f"NY takes the London high {pct(a['ny_takes_lon_h'])} / London low {pct(a['ny_takes_lon_l'])} of days")
    L.append("Tested 2017-2025 on unseen years; odds were well calibrated. Base rates, not signals - no direction call.")
    return L


def main():
    now = datetime.now(CT)
    if "--at" in sys.argv:                          # dry-run at a past moment, e.g. --at "2026-10-16 10:30" (Chicago)
        now = datetime.strptime(sys.argv[sys.argv.index("--at") + 1], "%Y-%m-%d %H:%M").replace(tzinfo=CT)
    if now.weekday() >= 5 and not DRY:
        return
    mins = now.hour * 60 + now.minute
    if not (8 * 60 + 30 <= mins < 15 * 60 + 15) and not DRY:
        return
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    bp = st.get("brain_pred") or {}
    sess = now.date()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if state.get("date") != str(sess):
        state = {"date": str(sess), "sent": [], "chk": None}
    start = datetime(sess.year, sess.month, sess.day, 17, 0, tzinfo=CT) - timedelta(days=1)
    ALL = [b for b in bars() if b[0] <= now]
    B = [b for b in ALL if start <= b[0]]
    if len(B) < 60:
        print("not enough bars (holiday / no data)"); return
    o = B[0][1]; hi = max(b[2] for b in B); lo = min(b[3] for b in B); px = B[-1][4]
    so = (hi - lo) / o; asof = B[-1][0].astimezone(NY)
    same = bp.get("date") == str(sess) or "--at" in sys.argv
    pred = float(bp.get("pred") or 0) if same else 0.0
    chk = None
    for c in IM:                                   # latest checkpoint already passed
        hh, mm = map(int, c.split(":"))
        if mins >= hh * 60 + mm: chk = c
    lines = [f"NQ {px:,.0f} | range so far {hi - lo:,.0f} pts ({so * 100:.2f}%), high {hi:,.0f} / low {lo:,.0f} "
             f"| data as of {asof:%H:%M} NY (may lag a few minutes)"]
    upd = None
    how = "re-estimated at {} CT checkpoint; tested 2019-2025, band held 80%"
    if pred and chk:
        m = IM[chk]
        lf = m["a"] + m["b_pred"] * math.log(pred) + m["b_so"] * math.log(max(so, 1e-5))
        q = m
        if NN and len(IM) == 15:
            try:
                volh = json.load(open(VOLH)) if os.path.exists(VOLH) else {}
                lnn, (vc, v30) = nn_logrange(B, o, so, pred, chk, bp, volh)
                lf = (lf + lnn) / 2; q = NN["bands"][chk]
                how = "brain + neural net, re-estimated at {} CT; tested 2019-2025: 3% more accurate than without the net, band held 80%"
                if not DRY and state.get("chk") != chk:                  # remember today's volume at this checkpoint
                    for key, v in ((chk, vc), (chk + "_30", v30)):
                        volh[key] = (volh.get(key, []) + [v])[-20:]
                    json.dump(volh, open(VOLH, "w"))
            except Exception as e:
                print("neural net skipped:", e)
        f50 = max(math.exp(lf + q["q50"]), so); f10 = max(math.exp(lf + q["q10"]), so); f90 = max(math.exp(lf + q["q90"]), so)
        upd = (f10, f50, f90)
        P = lambda x: f"{x * o:,.0f}"
        lines += [f"Brain this morning: ~{P(pred)} pts for the day ({pred * 100:.2f}%) - {so / pred:.0%} of it already used.",
                  f"Updated with what happened so far: full day ~{P(f50)} pts (80%: {P(f10)}-{P(f90)}) "
                  f"-> typically ~{P(f50 - so)} more pts to come (80%: {P(f10 - so)}-{P(f90 - so)}).",
                  f"({how.format(chk)})"]
        if bp.get("high_far"):
            lines.append(f"Far levels today: high {bp['high_far']:,.0f} / low {bp['low_far']:,.0f} (~90% of days stay inside each)")
    elif not pred:
        lines.append("(no brain forecast for this session)")
    alerts = []
    if pred and upd:
        f10, f50, f90 = upd; P = lambda x: f"{x * o:,.0f}"
        if mins >= 9 * 60 and "upd10" not in state["sent"]:
            alerts.append(("upd10", "🧠 10:00 NY update - brain re-estimates today's range", 0x7048E8,
                           [lines[1], lines[2], "",
                            ("Already a big day - the rest of the session usually adds less than the morning suggested."
                             if so / pred > 0.8 else
                             "Quiet so far - most of today's move is probably still ahead." if so / pred < 0.45 else
                             "On track for a normal-sized day.")]))
        for lvl, key in ((1.0, "used100"), (1.3, "used130")):
            if so >= pred * lvl and key not in state["sent"]:
                alerts.append((key, f"📏 {lvl:.0%} of today's expected range used ({hi - lo:,.0f} pts)", 0xF08C00,
                               [f"Brain expected ~{P(pred)} pts today; NQ has already moved {hi - lo:,.0f}.",
                                f"On past days like this, the rest of the session added ~{P(f50 - so)} pts more "
                                f"(80%: {P(f10 - so)}-{P(f90 - so)}) - beyond today's high or low, not necessarily one direction.",
                                "Big moves are usually done early: be careful chasing late, size for a stretched market."]))
    if same and bp.get("high_far"):
        if hi >= bp["high_far"] and "farhigh" not in state["sent"]:
            s = FAR["up"]
            alerts.append(("farhigh", f"🔺 NQ hit the brain's FAR HIGH {bp['high_far']:,.0f}", 0xE03131,
                           [f"Only ~{s['far_hit_rate']:.0%} of days reach this level.",
                            f"On those days the high ran a further median {s['beyond_median_pct']:.2f}% (~{s['beyond_median_pct'] / 100 * o:,.0f} pts; "
                            f"80% within {s['beyond_p80_pct'] / 100 * o:,.0f} pts) and {s['closed_back_inside']:.0%} closed back below it.",
                            "Stretched day - not a short signal by itself (no tested direction edge)."]))
        if lo <= bp["low_far"] and "farlow" not in state["sent"]:
            s = FAR["down"]
            alerts.append(("farlow", f"🔻 NQ hit the brain's FAR LOW {bp['low_far']:,.0f}", 0xE03131,
                           [f"Only ~{s['far_hit_rate']:.0%} of days reach this level.",
                            f"On those days the low ran a further median {s['beyond_median_pct']:.2f}% (~{s['beyond_median_pct'] / 100 * o:,.0f} pts; "
                            f"80% within {s['beyond_p80_pct'] / 100 * o:,.0f} pts) and {s['closed_back_inside']:.0%} closed back above it.",
                            "Selloffs past the far low tend to keep running - careful catching the knife."]))
    if mins >= 8 * 60 + 31 and "openread" not in state["sent"] and "--at" not in sys.argv:
        try:
            orl = open_read(ALL, sess, start)
        except Exception as e:
            orl = None; print("open read failed:", e)
        if orl:
            alerts.append(("openread", "🔮 " + orl[0], 0x1098AD, orl[1:]))
            if not DRY:
                st["powers"] = [f"{orl[0]} (posted {now.astimezone(LUX):%H:%M} Lux)"] + orl[1:]
                st["powers_raw"] = dict(RAW)
    for key, title, color, body in alerts:
        push(title, "\n".join(body) + f"\n\n_NQ {px:,.0f}, data as of {asof:%H:%M} NY. Base rates, not advice._", color)
        state["sent"].append(key)
    changed = bool(alerts) or state.get("chk") != chk
    state["chk"] = chk
    if not DRY:
        json.dump(state, open(STATE, "w"))
        if changed:
            st["live"] = [f"LIVE - {now.astimezone(LUX):%a %d %b %H:%M} Lux"] + lines
            json.dump(st, open(STATUS, "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    if "--ping" in sys.argv:
        print("live webhook set:", bool(os.environ.get("DISCORD_WEBHOOK_LIVE")))
        push("Live tracker online", "During every US session (15:30-22:15 Lux) I watch NQ against the brain's forecast and post "
             "here when: the 10:00 NY update is ready, today's expected range is used up, or NQ hits a far high/low. "
             "Ask anytime with /live.", 0x2F9E44)
    else:
        main()
