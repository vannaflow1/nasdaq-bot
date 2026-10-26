"""outlook.py - Volta's OVERNIGHT OUTLOOK for Nasdaq futures, posted before the US open (owner request 26 Oct 2026).

What the 12-year test said (tools/overnight_study.py, pre-declared, design 2014-21, holdout 2022-Jan 2026 looked at once;
results in knowledge/research_out/overnight_*.json):
  * DAY SIZE is predictable before the open. A busy overnight session (high-low range vs its last 20 nights) means a
    bigger day; a quiet one a smaller day. Holdout corr +0.21 (p 0.0001). This is the main thing the outlook adds.
  * DAY DIRECTION is not. 14 inputs (overnight/Asia/London move, gap vs yesterday's range, yesterday's move, 5-day trend,
    VIX, VIX term structure, 10-year yield, dollar, tech-vs-S&P, red-folder releases, FOMC) - none gives better up/down
    odds than the normal drift in the holdout. Yesterday's move reverses a little in SIZE (corr -0.08) but not in odds
    (52.5% vs 52.2% up). So the outlook does NOT call a direction; the hourly noise-band bias (bias.py) stays the only
    tested direction input.
  * Overnight move agreeing with the hourly band bias: +4 to +5 points of hit rate in both periods, not significant in
    either (p 0.07 / 0.12). Logged live from now on as 'watching', not used to change the call.
  * News / events: no headline history to test, so they are CONTEXT (what is scheduled, what moved overnight), never a
    direction call. An optional Gemini summary of the headlines is labelled the same way.
Writes knowledge/outlook_today.json (bias.py reads it) and posts to the live Discord channel once per day.
Run: python outlook.py [--dry]"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
CT, LUX = ZoneInfo("America/Chicago"), ZoneInfo("Europe/Luxembourg")
OUT = os.path.join(K, "outlook_today.json"); LOG = os.path.join(K, "outlook_log.csv"); SEEN = os.path.join(K, "outlook_news_seen.json")
# on_range_z quintile cuts (2014-Jan 2026) and the median RTH |open->close| move / high-low range in % per bucket (2020+)
CUTS = [0.67, 0.87, 1.11, 1.53]
SIZE = [("QUIET", 0.43, 1.09), ("CALMER", 0.58, 1.32), ("NORMAL", 0.65, 1.28), ("BUSIER", 0.73, 1.44), ("WIDE", 0.86, 1.78)]


def yahoo(sym, start, end):
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&period1={int(start.timestamp())}"
         f"&period2={int(end.timestamp())}&includePrePost=true")
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    return pd.DataFrame({"ts": [datetime.fromtimestamp(t, timezone.utc).astimezone(CT).replace(tzinfo=None) for t in r["timestamp"]],
                         "high": q["high"], "low": q["low"], "close": q["close"]}).dropna()


def bars(now_utc):
    parts = []
    for k in range(5):
        try: parts.append(yahoo("NQ%3DF", now_utc - timedelta(days=7 * (k + 1)), now_utc - timedelta(days=7 * k)))
        except Exception as e: print("yahoo chunk", k, type(e).__name__)
    import glob
    for f in sorted(glob.glob(os.path.join(K, "data", "archive", "NQ_*.csv.gz"))):
        try: parts.append(pd.read_csv(f, parse_dates=["ts"])[["ts", "high", "low", "close"]])
        except Exception: pass
    return pd.concat(parts).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def nights(b):
    """per trading day d: overnight window 17:00 CT (d-1) -> 08:29 CT (d); previous RTH 08:30-14:59 CT (d-1)."""
    b = b.copy(); m = b.ts.dt.hour * 60 + b.ts.dt.minute
    b["day"] = (b.ts.dt.normalize() + pd.to_timedelta((m >= 17 * 60).astype(int), unit="D")).dt.date
    b["m"] = (m - 17 * 60) % 1440
    out = {}
    for d, g in b.groupby("day"):
        if pd.Timestamp(d).weekday() >= 5: continue
        on = g[g.m < 930]; rth = g[(g.m >= 930) & (g.m < 1320)]; asia = g[g.m < 540]
        out[d] = {"on_hi": on.high.max() if len(on) else np.nan, "on_lo": on.low.min() if len(on) else np.nan,
                  "pre": on.close.iloc[-1] if len(on) else np.nan, "asia_end": asia.close.iloc[-1] if len(asia) else np.nan,
                  "on_n": len(on), "rth_hi": rth.high.max() if len(rth) else np.nan, "rth_lo": rth.low.min() if len(rth) else np.nan,
                  "rth_c": rth.close.iloc[-1] if len(rth) else np.nan, "rth_n": len(rth)}
    return out


def macro_line():
    try:
        M = pd.read_csv(os.path.join(K, "macro_daily.csv")).iloc[-1]
        term = M.vix / M.vix3m if M.vix3m else np.nan
        return (f"Last US close ({M.date}): VIX {M.vix:.1f} ({M.vix_chg:+.1f}%), VIX/VIX3M {term:.2f} "
                f"({'inverted - stress' if term > 1 else 'normal'}), 10y {M.us10y:.2f}% ({M.us10y_chg_bp:+.0f} bp), "
                f"dollar {M.dxy_ret:+.2f}%, NQ vs S&P {M.nq_vs_es:+.2f}%."), {"vix": float(M.vix), "vix_term": float(term)}
    except Exception as e:
        return f"Macro close data unavailable ({type(e).__name__}).", {}


def events_lines(today):
    L = []
    try:
        import redfolder; f = redfolder.today_flags(today); L += [f"🔴 {x}" for x in f.get("red_events", [])]
    except Exception as e: print("redfolder", type(e).__name__)
    try:
        import events as EV
        L += [f"📅 {x}" for x in EV.macro_events(today) if not L or "FOMC" in x]
        er = EV.earnings_rows(today); L += [f"💼 {s} earnings {w}" for s, w in er[:8]]
    except Exception as e: print("events", type(e).__name__)
    return L


def headlines():
    try:
        import news
        lines, _, by = news.digest(SEEN, hours=16, top=6)
        return lines, by
    except Exception as e:
        print("news", type(e).__name__); return [], "none"


def gemini_summary(head, ctx):
    try:
        import gemini
        if not head or gemini.calls_left() < 5: return None
        p = ("You write 2-3 plain sentences for a Nasdaq futures trader before the US open: what happened overnight and what "
             "is scheduled today, using ONLY the facts below. Do NOT predict direction, do not say bullish/bearish, no advice.\n\n"
             + ctx + "\nHeadlines:\n" + "\n".join(head))
        t = gemini.ask(p, temperature=0.1, max_tokens=300).strip()
        return t if 20 < len(t) < 900 else None
    except Exception as e:
        print("gemini", type(e).__name__); return None


def build(now_ct):
    now_utc = now_ct.replace(tzinfo=CT).astimezone(timezone.utc)
    N = nights(bars(now_utc)); today = now_ct.date(); days = sorted(d for d in N if d <= today)
    if today not in N or N[today]["on_n"] < 300: return None
    prev = [d for d in days if d < today and N[d]["rth_n"] >= 300]
    if not prev: return None
    y = N[prev[-1]]; t = N[today]
    rng_hist = [(N[d]["on_hi"] - N[d]["on_lo"]) / N[d]["pre"] for d in prev[-20:] if N[d]["on_n"] >= 600]
    on_rng = (t["on_hi"] - t["on_lo"]) / t["pre"]; z = on_rng / np.median(rng_hist) if len(rng_hist) >= 8 else np.nan
    k = int(np.digitize(z, CUTS)) if np.isfinite(z) else 2; name, mv, rg = SIZE[k]
    on_ret = t["pre"] / y["rth_c"] - 1; asia = t["asia_end"] / y["rth_c"] - 1; lon = t["pre"] / t["asia_end"] - 1
    loc = ("ABOVE yesterday's high" if t["pre"] > y["rth_hi"] else "BELOW yesterday's low" if t["pre"] < y["rth_lo"]
           else "inside yesterday's range")
    px = t["pre"]; mac, mvals = macro_line()
    o = {"date": str(today), "made_ct": now_ct.strftime("%H:%M"), "price": round(px, 2), "on_ret": round(on_ret, 5),
         "asia_ret": round(asia, 5), "london_ret": round(lon, 5), "on_range_pct": round(on_rng * 100, 3),
         "on_range_z": None if not np.isfinite(z) else round(float(z), 2), "size": name,
         "exp_move_pts": round(px * mv / 100), "exp_range_pts": round(px * rg / 100), "location": loc,
         "overnight_dir": "UP" if on_ret > 0 else "DOWN", **mvals}
    return o


def text(o, ev, head, by, summ, mac):
    sz = {"QUIET": "a SMALLER day than usual", "CALMER": "a slightly smaller day", "NORMAL": "a normal-size day",
          "BUSIER": "a slightly bigger day", "WIDE": "a BIGGER day than usual"}[o["size"]]
    lines = [f"🌙 Overnight: NQ {o['price']:,.2f}, {o['on_ret'] * 100:+.2f}% since yesterday's 15:00 CT close "
             f"(Asia {o['asia_ret'] * 100:+.2f}%, London {o['london_ret'] * 100:+.2f}%), {o['location']}.",
             f"📏 Expected day size: {o['size']} - overnight range {o['on_range_pct']:.2f}% = {o['on_range_z']}x its normal. "
             f"History says {sz}: typical open-to-close move ~{o['exp_move_pts']} pts, high-low range ~{o['exp_range_pts']} pts. "
             f"(Tested 2014-2026: this part works.)",
             "🧭 Direction: no call before the open. 14 pre-open inputs tested over 12 years - none beats the normal drift "
             "on up/down odds. Direction comes from the hourly noise-band bias after the open "
             f"(overnight was {o['overnight_dir']}; I'll note in each bias post whether they agree - that part is still being watched).",
             f"🌍 {mac}"]
    if ev: lines.append("Today: " + " · ".join(ev))
    if summ: lines.append(f"📰 {summ}\n(Summary of headlines by Gemini - context, not a signal.)")
    elif head: lines.append("📰 Overnight headlines (" + by + "-ranked, context only):\n" + "\n".join(head[:5]))
    return "\n".join(lines)


def main():
    dry = "--dry" in sys.argv; force = "--force" in sys.argv
    now = datetime.now(CT).replace(tzinfo=None)
    if not force and (now.weekday() >= 5 or not (7 * 60 <= now.hour * 60 + now.minute < 8 * 60 + 30)):
        print("outside 07:00-08:29 CT"); return
    if not force and os.path.exists(OUT) and json.load(open(OUT)).get("date") == str(now.date()):
        print("already posted today"); return
    o = build(now)
    if o is None: print("no overnight data"); return
    ev = events_lines(now.date()); head, by = headlines(); mac, _ = macro_line()
    summ = gemini_summary(head, json.dumps({k: o[k] for k in ("price", "on_ret", "asia_ret", "london_ret", "location", "size")}) + "\n" + mac
                          + "\nScheduled: " + "; ".join(ev))
    body = text(o, ev, head, by, summ, mac); print(body)
    if dry: return
    json.dump(o, open(OUT, "w"), indent=1)
    pd.DataFrame([o]).to_csv(LOG, mode="a", header=not os.path.exists(LOG), index=False)
    import qqq_gex_daily as q
    lux = datetime(now.year, now.month, now.day, 8, 30, tzinfo=CT).astimezone(LUX).strftime("%H:%M")
    q.push(f"NQ overnight outlook - US open {lux} Lux", body, hook=os.environ.get("DISCORD_WEBHOOK_LIVE") or None)


if __name__ == "__main__":
    main()
