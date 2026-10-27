"""bias.py - Volta's intraday BIAS for Nasdaq futures (owner request, 23 Oct 2026). Separate from the prop-edge hunt.

What it is (and what it is not):
  * No pre-open forecast. Volta tested 147+ pre-market direction signals (options positioning, Greeks, SPX flow, overnight
    levels): none predicts the day's direction better than chance. A morning "bias" would be a coin flip dressed up.
  * What DOES carry direction (F2/F10, 12 years of NQ data): once price leaves its NORMAL NOISE BAND for that time of
    day, the rest of the session leans the same way. Band = today's open +- 1.2 x the average distance from the open at
    that minute over the last 14 sessions. Checked hourly 09:00-14:00 Chicago (16:00-21:00 Luxembourg, 15:00-20:00 in
    the weeks the US and EU clocks differ).
  * Measured on NQ 2014-2026 (every hourly check, outcome = close 14:59 CT vs price at the check):
        LONG bias  -> rest of day up 58.1% (n 3,074)     SHORT bias -> rest of day down 49.9% (n 2,909)
        no bias    -> rest of day up 54.2% (normal upward drift)
    i.e. about +4 percentage points over the drift in both directions - a real but SMALL lean, not a prediction.
Posts to the live Discord channel at the first check of the day and whenever the bias changes; logs every check to
knowledge/bias_log.csv and grades the day after the close (running scoreboard).
Morning outlook (outlook.py, 26 Oct 2026): each post adds the expected day size and whether the overnight move agrees;
the agreement is logged (columns overnight/agree/day_size) so it can be judged on live data - it does not change the call.
Morning outlook (outlook.py, 26 Oct 2026): each post adds the expected day size and whether the overnight move agrees;
the agreement is logged (columns overnight/agree/day_size) to be judged on live data - it does not change the call.
Run: python bias.py [--dry] [--at "2026-10-23 10:05"]   (Chicago time for --at; dry runs only)"""
import json, os, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
CT, LUX = ZoneInfo("America/Chicago"), ZoneInfo("Europe/Luxembourg")
LOG = os.path.join(K, "bias_log.csv")
MULT, LOOKBACK, MIN_HIST = 1.2, 14, 5
CHECKS = [9, 10, 11, 12, 13, 14]                              # Chicago hours
ODDS = {"LONG": "the rest of the day closed HIGHER 58% of the time", "SHORT": "the rest of the day closed LOWER 50% of the time "
        "(vs 46% on an average check - the market drifts up)", "NONE": "it closed higher 54% of the time - just the normal upward drift"}


def yahoo(sym="NQ%3DF", start=None, end=None):
    q = f"period1={int(start.timestamp())}&period2={int(end.timestamp())}" if start else "range=5d"
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&{q}&includePrePost=true"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["chart"]["result"][0]
    qd = r["indicators"]["quote"][0]
    return pd.DataFrame({"ts": [datetime.fromtimestamp(t, timezone.utc).astimezone(CT).replace(tzinfo=None) for t in r["timestamp"]],
                         "open": qd["open"], "close": qd["close"]}).dropna()


def bars(now):
    """1-minute NQ bars, Chicago time: the nightly archive + Yahoo's last ~4 weeks (7-day chunks) + today."""
    parts = []
    import glob
    for f in sorted(glob.glob(os.path.join(K, "data", "archive", "NQ_*.csv.gz"))):
        try: parts.append(pd.read_csv(f, parse_dates=["ts"])[["ts", "open", "close"]])
        except Exception: pass
    end = datetime.now(timezone.utc)
    for k in range(4):
        try: parts.append(yahoo(start=end - timedelta(days=7 * (k + 1)), end=end - timedelta(days=7 * k)))
        except Exception as e: print("yahoo chunk", k, type(e).__name__)
    try: parts.append(yahoo())
    except Exception as e: print("yahoo 5d", type(e).__name__)
    b = pd.concat(parts).drop_duplicates("ts").sort_values("ts")
    return b[b.ts <= now]


def sessions(b):
    """RTH minute grid 08:30-14:59 CT per date: open of the 08:30 bar and closes per minute."""
    b = b.copy(); b["d"] = b.ts.dt.date; b["m"] = b.ts.dt.hour * 60 + b.ts.dt.minute - 510
    b = b[(b.m >= 0) & (b.m < 390)]; out = {}
    for d, g in b.groupby("d"):
        g = g.drop_duplicates("m").set_index("m")
        if 0 not in g.index: continue
        c = g.close.reindex(range(390)).ffill(); out[d] = (float(g.open.loc[0]), c.to_numpy(float), len(g))
    return out


def read_log():
    L = pd.read_csv(LOG) if os.path.exists(LOG) else pd.DataFrame(columns=["date", "check_ct", "bias", "price", "open", "band_pct", "dist_bands", "close", "result", "overnight", "agree", "day_size"])
    L["result"] = L["result"].astype(object)                  # all-empty column reads as float -> grading crashed (23 Oct)
    return L


def publish(now, L=None, early=None):
    """status.json["bias"] for the Discord /bias command: today's bias checks, the morning outlooks, the scoreboard."""
    try:
        L = read_log() if L is None else L; today = str(now.date())
        lux = lambda h: datetime(now.year, now.month, now.day, h, 0, tzinfo=CT).astimezone(LUX).strftime("%H:%M")
        nowlux = datetime(now.year, now.month, now.day, now.hour, now.minute, tzinfo=CT).astimezone(LUX)
        out = [f"🧭 NQ BIAS - {nowlux:%a %d %b}, as of {nowlux:%H:%M} Lux"]
        t = L[L.date.astype(str) == today].sort_values("check_ct")
        if len(t):
            last = t.iloc[-1]; head = {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "NONE": "⚪ NO BIAS"}[last.bias]
            out.append(f"Now: {head} (check {int(last.check_ct):02d}:00 CT = {lux(int(last.check_ct))} Lux) - NQ {last.price:,.2f}, "
                       f"{(last.price / last.open - 1) * 100:+.2f}% from the 08:30 CT open, noise band ±{last.band_pct:.2f}%.")
            out.append("Today: " + " → ".join(f"{lux(int(r.check_ct))} {r.bias}" for r in t.itertuples()))
            if last.bias != "NONE": out.append("Meaning: a small lean (~4 pts over the normal drift), not a prediction.")
        elif now.weekday() >= 5: out.append("Weekend - next checks Monday from the NY open + 30 min.")
        else:
            mins = now.hour * 60 + now.minute
            if mins < 8 * 60 + 30:
                out.append(f"Market not open yet (NY open {datetime(now.year, now.month, now.day, 8, 30, tzinfo=CT).astimezone(LUX):%H:%M} Lux). First bias check at {lux(9)} Lux, then hourly until {lux(14)} Lux.")
            else:
                out.append(f"Market open - the first real bias check is at {lux(9)} Lux (30 min in), then hourly until {lux(14)} Lux.")
                if early:
                    b, px, pct, band = early
                    out.append(f"Early read (as of {datetime(now.year, now.month, now.day, now.hour, now.minute, tzinfo=CT).astimezone(LUX):%H:%M} Lux): "
                               f"{ {'LONG': '🟢 above', 'SHORT': '🔴 below', 'NONE': '⚪ inside'}[b]} its normal noise band "
                               f"(NQ {px:,.2f}, {pct:+.2f}% from the open, band ±{band:.2f}%). Reads this early were right only 51-58% of the "
                               "time in 12 years (weaker before 2022) - a heads-up, not a bias.")
        for fn, nm in (("outlook_today.json", "NY outlook"), ("london_today.json", "London outlook")):
            try:
                o = json.load(open(os.path.join(K, fn)))
                if o.get("date") != today: continue
                if nm == "NY outlook":
                    out.append(f"{nm}: {o['size']} day expected (~{o['exp_range_pts']} pts high-low, ~{o['exp_move_pts']} pts open-to-close); "
                               f"overnight {o['on_ret'] * 100:+.2f}% ({o['overnight_dir']}), {o['location']}.")
                    if len(t) and t.iloc[-1].bias != "NONE":
                        ag = (o["overnight_dir"] == "UP") == (t.iloc[-1].bias == "LONG")
                        out.append(f"Overnight {'AGREES' if ag else 'DISAGREES'} with the bias (agreeing was ~4-5 pts better in tests, not proven - tracked).")
                else:
                    out.append(f"{nm}: {o['size']} London (~{o['exp_move_pts']} pts London-to-NY open); Asia range "
                               f"{o['asia_lo']:,.2f}-{o['asia_hi']:,.2f}. London breakouts tended to reverse - no London call.")
            except Exception: pass
        a = L[L.bias.isin(["LONG", "SHORT"]) & L.result.isin(["right", "wrong"])]
        if len(a): out.append(f"Scoreboard: {(a.result == 'right').sum()}/{len(a)} graded checks right "
                              f"({(a.result == 'right').mean():.0%}) over {a.date.nunique()} days; history says ~54-58%.")
        if now.hour * 60 + now.minute < 8 * 60 + 30 and now.weekday() < 5:
            out.append("Day direction can't be called before the open (14 inputs tested, 12 years); day size can.")
        sp = os.path.join(HERE, "status.json"); st = json.load(open(sp)) if os.path.exists(sp) else {}
        st["bias"] = out; json.dump(st, open(sp, "w"), indent=1)
    except Exception as e:
        print("publish failed:", type(e).__name__, e)


def main():
    dry = "--dry" in sys.argv
    now = datetime.strptime(sys.argv[sys.argv.index("--at") + 1], "%Y-%m-%d %H:%M") if "--at" in sys.argv else datetime.now(CT).replace(tzinfo=None)
    S = sessions(bars(now)); today = now.date(); L = read_log()
    # 1) grade finished days (close 14:59 CT)
    for d in sorted({r for r in L.date.astype(str)}):
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        if dd in S and (dd < today or now.hour * 60 + now.minute >= 15 * 60 + 2):
            close = S[dd][1][389]; m = (L.date.astype(str) == d) & L.result.isna()
            if m.any() and np.isfinite(close):
                L.loc[m, "close"] = close
                L.loc[m, "result"] = np.where(L.loc[m, "bias"] == "NONE", "n/a",
                                              np.where((close - L.loc[m, "price"]) * np.where(L.loc[m, "bias"] == "LONG", 1, -1) > 0, "right", "wrong"))
                if not dry:                                   # scoreboard for every newly graded day
                    g = L[(L.date.astype(str) == d) & L.bias.isin(["LONG", "SHORT"])]; a = L[L.bias.isin(["LONG", "SHORT"]) & L.result.isin(["right", "wrong"])]
                    if len(g):
                        import qqq_gex_daily as q
                        q.push("🧭 Bias scoreboard", f"{d}: {(g.result == 'right').sum()}/{len(g)} bias checks right. Since start: "
                               f"{(a.result == 'right').mean():.0%} of {len(a)} (history says ~54% is the honest expectation).",
                               hook=os.environ.get("DISCORD_WEBHOOK_LIVE") or None)
    if now.weekday() >= 5:
        if not dry: L.to_csv(LOG, index=False); publish(now, L)
        print("weekend"); return
    # 2) today's check
    h = max([c for c in CHECKS if now.hour * 60 + now.minute >= c * 60] or [None], key=lambda x: x or -1)
    if h is None or now.hour * 60 + now.minute > 15 * 60 or today not in S:
        early = None
        if h is None and today in S and 8 * 60 + 35 <= now.hour * 60 + now.minute < 9 * 60:
            try:
                t = now.hour * 60 + now.minute - 510; o, ct_, _ = S[today]; c = ct_[t - 1]
                hist = [S[d] for d in sorted(S) if d < today and S[d][2] >= 300][-LOOKBACK:]
                sig = float(np.nanmean([abs(hc[t - 1] / ho - 1) for ho, hc, _ in hist])); band = MULT * sig
                if np.isfinite(c): early = ("LONG" if c > o * (1 + band) else "SHORT" if c < o * (1 - band) else "NONE", c, (c / o - 1) * 100, band * 100)
            except Exception as e: print("early read", type(e).__name__)
        (None if dry else (L.to_csv(LOG, index=False), publish(now, L, early))); print("no check now", early); return
    if ((L.date.astype(str) == str(today)) & (L.check_ct == h)).any():
        (None if dry else (L.to_csv(LOG, index=False), publish(now, L))); print("already checked", h); return
    hist = [S[d] for d in sorted(S) if d < today and S[d][2] >= 300][-LOOKBACK:]
    if len(hist) < MIN_HIST: print("not enough history:", len(hist)); (None if dry else (L.to_csv(LOG, index=False), publish(now, L))); return
    t = h * 60 - 510; o, c_today, _ = S[today]; c = c_today[t - 1]
    sig = float(np.nanmean([abs(hc[t - 1] / ho - 1) for ho, hc, _ in hist])); band = MULT * sig
    dist = (c / o - 1) / sig if sig > 0 else 0.0
    bias = "LONG" if c > o * (1 + band) else "SHORT" if c < o * (1 - band) else "NONE"
    ol = {}
    try:
        ol = json.load(open(os.path.join(K, "outlook_today.json")))
        ol = ol if ol.get("date") == str(today) else {}
    except Exception: pass
    on_dir = ol.get("overnight_dir", ""); agree = "" if bias == "NONE" or not on_dir else ("yes" if (on_dir == "UP") == (bias == "LONG") else "no")
    prev = L[L.date.astype(str) == str(today)].sort_values("check_ct")
    L = pd.concat([L, pd.DataFrame([{"date": str(today), "check_ct": h, "bias": bias, "price": round(c, 2), "open": round(o, 2),
                                     "band_pct": round(band * 100, 3), "dist_bands": round(dist / MULT, 2),
                                     "overnight": on_dir, "agree": agree, "day_size": ol.get("size", "")}])], ignore_index=True)
    first = not len(prev); changed = len(prev) and prev.bias.iloc[-1] != bias
    lux = datetime(now.year, now.month, now.day, h, 0, tzinfo=CT).astimezone(LUX).strftime("%H:%M")
    head = {"LONG": "🟢 LONG bias", "SHORT": "🔴 SHORT bias", "NONE": "⚪ No bias"}[bias]
    body = (f"{head} at {h:02d}:00 Chicago ({lux} Lux). NQ {c:,.2f}, {(c / o - 1) * 100:+.2f}% from the 08:30 open; "
            f"normal noise band now ±{band * 100:.2f}% ({len(hist)} sessions).\n"
            f"History (NQ 2014-2026): at checks like this, {ODDS[bias]}.\n"
            + ("A small lean (about 4 points over the normal drift), not a prediction - it can flip; I post again if it does."
               if bias != "NONE" else "Price is inside its normal noise: no lean beyond the usual drift. I post again if that changes.")
            + (f"\nMorning outlook: {ol['size']} day expected (~{ol['exp_range_pts']} pts high-low)"
               + (f"; overnight was {on_dir} - {'AGREES' if agree == 'yes' else 'DISAGREES'} with this bias "
                  "(agreeing days were ~4-5 pts better in both test periods, not proven yet - being tracked)" if agree else "")
               + "." if ol else ""))
    print(body)
    if not dry and (first or changed):
        import qqq_gex_daily as q
        q.push(f"NQ bias {h:02d}:00 CT: {bias}", body, hook=os.environ.get("DISCORD_WEBHOOK_LIVE") or None)
    if not dry: L.to_csv(LOG, index=False); publish(now, L)


if __name__ == "__main__":
    main()
