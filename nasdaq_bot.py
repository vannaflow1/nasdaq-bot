"""
nasdaq_bot.py - daily Nasdaq briefing pushed to your phone (ntfy).

  py nasdaq_bot.py --evening   after the US close (scheduled 22:35 Lux):
                               QQQ gamma reading (validated) + paper fly,
                               NDX/combined gamma log (building history),
                               tomorrow's events, the day's filtered news.
  py nasdaq_bot.py --morning   before the US open (scheduled 14:45 Lux):
                               today's events, overnight news, last gamma reading.
  py nasdaq_bot.py --trump     checks Trump's Truth Social for NEW market-relevant posts
                               and pushes them immediately (scheduled every 5 minutes).
  py nasdaq_bot.py --test      checks every data source and sends a test push.
                               Writes nothing to the history files.

Optional: put an Anthropic API key in config.json ("anthropic_api_key") to have
Claude re-rank the news; otherwise keyword ranking is used.
"""
import json, os, sys, traceback
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qqq_gex_daily as q          # validated QQQ GEX logic, history, paper trades, push()
import ndx, news, events, truth, playbook, analyst, levels, recap, brain, options_nerd, event_playbook

CFG_PATH = os.path.join(HERE, "config.json")
NDX_HIST = os.path.join(HERE, "ndx_history.csv")
SEEN = os.path.join(HERE, "news_seen.json")
TRUTH_SEEN = os.path.join(HERE, "truth_seen.json")
SPOTS = os.path.join(HERE, "qqq_closes.csv")
PREDS = os.path.join(HERE, "predictions.csv")
DAILY_LOG = os.path.join(HERE, "daily_log.csv")
STATUS = os.path.join(HERE, "status.json")
BRAIN_HOOK = os.environ.get("DISCORD_WEBHOOK_BRAIN", "")      # optional: separate #brain channel
NERD_HOOK = os.environ.get("DISCORD_WEBHOOK_NERD", "")        # optional: separate #options channel
_NDX = {}
RETIRED = os.path.join(HERE, "forecaster_retired.flag")   # created when the scorecard finds no edge
MAXLEN = 3800                       # ntfy message limit is 4096 bytes


def cfg():
    try:
        return json.load(open(CFG_PATH))
    except Exception:
        return {}


def lux_today():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Luxembourg")).date()
    except Exception:
        return date.today()


def next_trading_day(d):
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def clip(s):
    return s if len(s.encode()) <= MAXLEN else s.encode()[:MAXLEN].decode(errors="ignore") + "\n...(cut)"


# ------------------------------------------------------------------ gamma
def run_qqq(chain_file=None):
    """Runs the validated QQQ script; returns (text, ts, qqq_chain, spot)."""
    cache = {}
    orig = q.load_chain

    def cached(path=None):
        cache["r"] = orig(path)
        return cache["r"]
    q.load_chain = cached
    argv = sys.argv
    sys.argv = [argv[0]] + ([chain_file] if chain_file else [])
    q._LOG.seek(0); q._LOG.truncate()
    try:
        q.main()
    finally:
        sys.argv = argv
        q.load_chain = orig
    text = q._LOG.getvalue()
    if "r" not in cache:
        return text, None, None, None
    ts, d = cache["r"]
    return text, ts, d, q.spot_by_parity(d)


def run_ndx(ts_qqq, d_qqq, S_qqq, ndx_file=None, write=True):
    lines = []
    try:
        ts, d = ndx.parse(ndx.fetch(path=ndx_file))
        S = ndx.spot_by_parity(d)
        if not np.isfinite(S):
            return ["  NDX: no usable quotes (holiday/weekend?)"]
        _NDX["d"], _NDX["S"] = d, S
        g_ndx = ndx.dollar_gex(d, S)
        g_qqq = ndx.dollar_gex(d_qqq, S_qqq)
        comb = g_ndx + g_qqq
        ratio = ndx.gamma_ratio(d, S)
        h = pd.read_csv(NDX_HIST, parse_dates=["date"]) if os.path.exists(NDX_HIST) else \
            pd.DataFrame(columns=["date", "ndx_spot", "ndx_gex_usd", "qqq_gex_usd", "combined_usd"])
        h = h[h.date != ts]
        h = pd.concat([h, pd.DataFrame([{"date": ts, "ndx_spot": round(S, 2), "ndx_gex_usd": round(g_ndx),
                                         "qqq_gex_usd": round(g_qqq), "combined_usd": round(comb)}])])
        h = h.sort_values("date")
        if write:
            h.to_csv(NDX_HIST, index=False, date_format="%Y-%m-%d")
        past = h.combined_usd.iloc[:-1].tail(252).to_numpy(float)
        share = abs(g_ndx) / (abs(g_ndx) + abs(g_qqq)) if (g_ndx or g_qqq) else float("nan")
        lines.append(f"  NDX {S:,.0f}: dealer gamma ${g_ndx/1e9:+.2f}bn per 1% move "
                     f"(QQQ ${g_qqq/1e9:+.2f}bn) -> combined ${comb/1e9:+.2f}bn, NDX share {share:.0%}")
        if len(past) >= 126:
            lines.append(f"  combined rank vs last {len(past)} days: {(comb > past).mean():.2f}  (NOT yet validated)")
        else:
            lines.append(f"  combined rank: building history ({len(past)+1}/126 days) - QQQ rank is the one to use")
        if ratio is not None and not (0.8 < ratio < 1.25):
            lines.append(f"  !! NDX gamma convention check failed (ratio {ratio:.2f})")
        if ts != ts_qqq:
            lines.append(f"  !! NDX data date {ts.date()} != QQQ date {ts_qqq.date()}")
    except Exception as e:
        lines.append(f"  NDX: failed ({type(e).__name__}: {str(e)[:80]})")
    return lines


def last_qqq_reading():
    try:
        h = pd.read_csv(q.HIST, parse_dates=["date"]).sort_values("date")
        g, past = h.gexn.iloc[-1], h.gexn.iloc[:-1].tail(252).to_numpy(float)
        r = float((g > past).mean())
        qn = min(5, int(r * 5) + 1)
        return f"Last gamma reading ({h.date.iloc[-1].date()}): rank {r:.2f}, quintile {qn}\n  -> {q.QUINTILE_NOTE[qn]}"
    except Exception as e:
        return f"Last gamma reading unavailable ({type(e).__name__})"


# ------------------------------------------------------------------ news
def news_block(hours, top=8):
    key = cfg().get("anthropic_api_key")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    lines, status, by = news.digest(SEEN, hours=hours, top=top)
    failed = [k for k, v in status.items() if v.startswith("FAILED")]
    head = f"NEWS (last {hours}h, ranked by {by}):"
    body = lines or ["- nothing important passed the filter"]
    foot = [f"(sources down: {', '.join(failed)})"] if failed else []
    return [head] + body + foot


def _quintile(text):
    import re
    m = re.search(r"quintile (\d)", text)
    return int(m.group(1)) if m else None


def _after_close(day):
    e, _ = events.earnings_for(day)
    return [x.split()[0] for x in e if "after close" in x]


def _rank(text):
    import re
    m = re.search(r"rank vs last 252 days: ([0-9.]+)", text)
    return float(m.group(1)) if m else float("nan")


def nq_basis():
    """NQ futures / NDX index (the futures premium, ~0.3-1%). Yahoo daily closes, cached per run."""
    if "basis" in _NDX:
        return _NDX["basis"]
    b = 1.0
    try:
        f, i = brain.yahoo("NQ=F", "5d").close, brain.yahoo("^NDX", "5d").close
        common = f.index.intersection(i.index)
        if len(common):
            r = float(f[common[-1]] / i[common[-1]])
            if 0.985 < r < 1.03:
                b = r
    except Exception as e:
        print("NQ basis unavailable, using index level:", e)
    _NDX["basis"] = b
    return b


def nq_level(S_qqq):
    """NQ FUTURES (front month) level matching QQQ spot S_qqq: NDX level x the futures premium."""
    if np.isfinite(_NDX.get("S", np.nan)):
        ndx_lvl = _NDX["S"]
    else:
        try:
            h = pd.read_csv(NDX_HIST).dropna()
            r = h.iloc[-1]
            ndx_lvl = S_qqq * r.ndx_spot / pd.read_csv(SPOTS).spot.iloc[-1]
        except Exception:
            ndx_lvl = S_qqq * 41.1
    return ndx_lvl * nq_basis()


def write_status(**kw):
    old = {}
    try:
        old = json.load(open(STATUS))
    except Exception:
        pass
    new = json.loads(json.dumps({**old, **kw}, default=str))
    if all(new.get(k) == old.get(k) for k in kw):      # nothing changed -> no rewrite, no git commit
        return
    try:
        from zoneinfo import ZoneInfo
        new["updated"] = datetime.now(ZoneInfo("Europe/Luxembourg")).strftime("%a %d %b %H:%M Lux")
    except Exception:
        new["updated"] = datetime.now().strftime("%a %d %b %H:%M")
    json.dump(new, open(STATUS, "w"), indent=1)


def earnings_block(day, ts):
    rows = events.earnings_rows(day)
    moves, lines = [], []
    for sym, when in rows:
        try:
            m = levels.earnings_move(sym, day, when if when != "time n/a" else "after close", ts)
            if m:
                moves.append(m)
        except Exception as e:
            lines.append(f"  {sym} reports {when}: implied move n/a ({type(e).__name__})")
    return levels.earnings_lines(moves) + lines


def trump_block(hours):
    lines, err = truth.digest(hours=hours)
    head = [f"TRUMP on Truth Social (market-relevant, last {hours}h):"]
    if err:
        return head + [f"  ({err})"]
    return head + (lines or ["- nothing market-relevant"])


def run_forecast(ts, S, gamma_text, tmr):
    """Experimental directional forecast + automatic scorecard."""
    spots = analyst.log_spot(SPOTS, ts, S)            # always log the close (needed for grading)
    if os.path.exists(RETIRED):                        # retired: no more forecasts or scorecards
        return
    card = analyst.scorecard(PREDS, SPOTS)
    try:
        last = pd.read_csv(PREDS).iloc[-1]
        flines = [f"Latest forecast ({last['date']}): P(up next day) {float(last['p_up_1d']):.0%}, "
                  f"5 days {float(last['p_up_5d']):.0%} - EXPERIMENTAL", f"Drivers: {last.get('drivers', '')}", ""]
    except Exception:
        flines = ["No forecasts yet.", ""]
    write_status(forecast=flines + card)
    if any("NO EDGE" in l for l in card):
        with open(RETIRED, "w") as f:
            f.write(f"retired {datetime.now():%Y-%m-%d}\n" + "\n".join(card))
        q.push("Forecaster retired - no edge", "\n".join(
            ["The news-based direction forecast did not beat 'always up' in live testing,",
             "so it has been switched off. Gamma, events, Trump alerts and news keep running.", ""] + card),
            priority="high", tags="wastebasket")
        return
    key = cfg().get("anthropic_api_key")
    if not key:
        # forecasts come from the scheduled Claude task, which writes predictions.csv itself;
        # the bot only grades them
        if os.path.exists(PREDS) and "no graded" not in card[0]:
            q.push("Forecast scorecard", "\n".join(card), priority="low", tags="crystal_ball")
        return
    items, _ = news.fetch_all()
    cands = news.filter_news(items, set(), hours=24, top=15)
    heads = [f"- [{c['source']}] {c['title']}" for c in cands[:40]]
    trump, _ = truth.digest(hours=24, top=8)
    cal, _ = events.calendar_block(tmr, days=5)
    qn = _quintile(gamma_text)
    gl = f"QQQ gamma quintile {qn} of 5" + (" - " + q.QUINTILE_NOTE[qn] if qn else "")
    try:
        j = analyst.forecast(key, date_str=str(ts.date()), spot=S, recent=analyst.recent_closes(spots),
                             headlines=heads, trump=trump, events_lines=cal, gamma_line=gl)
    except Exception as e:
        q.push("Forecast: failed", f"{type(e).__name__}: {str(e)[:300]}", priority="low", tags="warning")
        return
    analyst.log_prediction(PREDS, ts, S, j)
    p1, p5 = j["p_up_1d"], j["p_up_5d"]
    word = lambda p: "BULLISH" if p >= 0.58 else "BEARISH" if p <= 0.46 else "NEUTRAL"
    body = ["EXPERIMENTAL - NOT A TRADE SIGNAL until the scorecard proves it.",
            f"Next session ({tmr:%a %d %b}): {word(p1)} - P(up) {p1:.0%}   (base rate {analyst.BASE_UP:.0%})",
            f"Next 5 sessions: {word(p5)} - P(up) {p5:.0%}   confidence: {j.get('confidence','?')}",
            "", "Why:"] + [f"- {d}" for d in j.get("drivers", [])] + \
           [f"Could be wrong if: {j.get('against','')}", ""] + card
    q.push(f"Forecast {tmr:%a}: {word(p1)} {p1:.0%} (unproven)", clip("\n".join(body)),
           priority="default", tags="crystal_ball")


# ------------------------------------------------------------------ cloud scheduling guards
RUNS = os.path.join(HERE, "runs.json")


def _runs():
    try:
        return json.load(open(RUNS))
    except Exception:
        return {}


def _mark(mode, value):
    r = _runs(); r[mode] = value
    json.dump(r, open(RUNS, "w"))


def _expected_session():
    """Most recent US session whose close (+20 min) has passed, as YYYY-MM-DD (weekdays)."""
    from zoneinfo import ZoneInfo
    ny = datetime.now(ZoneInfo("America/New_York"))
    d = ny.date()
    if ny.weekday() >= 5 or ny.hour * 60 + ny.minute < 16 * 60 + 20:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def cloud_should_run(mode):
    """GitHub cron runs twice (summer/winter time); run once, at the right local time."""
    from zoneinfo import ZoneInfo
    if mode == "--evening":
        if q.market_open_now():                   # never treat intraday data as a close
            return False
        exp = _expected_session()
        return _runs().get("evening") != exp
    lux = datetime.now(ZoneInfo("Europe/Luxembourg"))
    if lux.weekday() >= 5 or lux.hour * 60 + lux.minute < 14 * 60 + 30:
        return False
    return _runs().get("morning") != lux.date().isoformat()


# ------------------------------------------------------------------ modes
def nerd_step(d, S, ts, nq, dry=False):
    """Deep options read (greeks, vol surface, flows) - posted as its own message."""
    try:
        c = brain.yahoo("QQQ").close
        rv20 = float(np.log(c).diff().tail(20).std() * np.sqrt(252))
    except Exception:
        rv20 = None
    lines = options_nerd.read(d, S, ts, rv20=rv20, nq_ratio=nq / S, write=not dry)
    if dry:
        print("\n".join(lines)); return
    q.push(f"Options nerd - QQQ {pd.Timestamp(ts):%a %d %b}", clip("\n".join(lines)), tags="nerd",
           hook=NERD_HOOK or None)
    from zoneinfo import ZoneInfo
    lux = datetime.now(ZoneInfo("Europe/Luxembourg"))
    write_status(nerd=[f"Read from the US close ({pd.Timestamp(ts):%a %d %b}), made {lux:%H:%M} Lux. "
                       "Live refresh every 30 min once the US market opens (15:30 Lux).", ""] + lines)


def brain_step(d, S, ts, text, qn, rng, nq, dry=False):
    """Volta's brain: grade yesterday, forecast tomorrow's NQ range, recall similar days."""
    nxt = (pd.Timestamp(ts) + analyst.TRADING_DAY).date()          # holiday-aware
    im = rng["implied_pct"] / 100 if rng else float("nan")
    if dry:
        nqb, qb = brain.yahoo("NQ%3DF"), brain.yahoo("QQQ")
        f = brain.features(d, S, ts, _rank(text), qn, im, nxt, nqb, qb)
        print(json.dumps(f, indent=1)); print(brain.predict(f, float(nqb.close.iloc[-1]))); print(brain.recall(f))
        return
    fc, journal = brain.evening(d, S, ts, _rank(text), qn, im, nxt, nq)
    card = brain.scorecard()
    n_mem = sum(1 for _ in open(brain.MEM)) - 1
    q.push(fc[0].replace("🧠 ", ""), clip("\n".join(fc[1:] + ["", f"Memories: {n_mem:,} days"] + card)),
           priority="default", tags="brain", hook=BRAIN_HOOK or None)
    if journal:
        q.push("Brain journal: how I did", clip("\n".join(journal + [""] + card)),
               priority="low", tags="notebook", hook=BRAIN_HOOK or None)
    write_status(brain=fc + ["", f"Memories: {n_mem:,} days"] + card, brain_journal=journal or None,
                 brain_pred=dict(brain.LAST) or None)


def evening(chain_file=None, ndx_file=None):
    text, ts, d, S = run_qqq(chain_file)
    if ts is None:                                   # skipped (market open) or failed early
        q.push("QQQ GEX: skipped", text.strip() or "no output", tags="warning")
        return
    gamma = [l for l in text.splitlines() if not l.startswith(("downloading", "  got "))]
    gamma += ["", "NDX (logging, not yet validated):"] + run_ndx(ts, d, S, ndx_file)
    tmr = next_trading_day(ts.date())
    qn = _quintile(text)
    level, acts = playbook.advise(qn, events.macro_events(tmr), truth.hot(18),
                                  _after_close(tmr))
    advice = playbook.render(level, acts)
    advice[0] = advice[0].replace("FOR YOU", f"FOR YOU TOMORROW ({tmr:%a %d %b})")
    nq = nq_level(S)
    try:
        rng = levels.expected_range(d, S, ts, qn, nq)
    except Exception:
        rng = None
    rlines = levels.range_lines(rng)
    try:
        chains = [(d, S, nq / S)] + ([(_NDX["d"], _NDX["S"], nq_basis())] if "d" in _NDX else [])
        wlines = levels.wall_lines(levels.walls(chains, nq), nq, S / nq)
    except Exception as e:
        wlines = [f"  gamma walls: n/a ({type(e).__name__})"]
    title = f"Tomorrow: risk {level}" + (" - size down" if level in ("ELEVATED", "HIGH") else "")
    q.push(title, clip("\n".join(advice + ["", "EXPECTED RANGE TOMORROW:"] + rlines +
                                 ["", "GAMMA WALLS:"] + wlines + ["", "DETAILS:"] + gamma).strip()),
           priority="high" if level in ("ELEVATED", "HIGH") else "default",
           tags="chart_with_upwards_trend")

    try:
        brain_step(d, S, ts, text, qn, rng, nq)
    except Exception as e:
        q.push("Brain error", f"{type(e).__name__}: {e}", priority="low", tags="warning", hook=BRAIN_HOOK or None)

    try:
        nerd_step(d, S, ts, nq)
    except Exception as e:
        q.push("Options nerd error", f"{type(e).__name__}: {e}", priority="low", tags="warning", hook=NERD_HOOK or None)

    elines = earnings_block(tmr, ts)
    write_status(**{"for": f"{tmr:%a %d %b}", "advice": advice, "gamma": gamma[:6], "range": rlines,
                    "walls": wlines, "earnings": elines or ["  no megacap earnings tomorrow"], "level": level})
    try:
        recap.log_day(DAILY_LOG, ts, _rank(text), qn, rng, level)
    except Exception:
        pass

    cal, cerr = events.calendar_block(tmr, days=5)
    msg = ["UPCOMING (next 5 trading days):"] + cal
    if elines:
        msg += ["", "EARNINGS - what options price:"] + elines
    if cerr:
        msg.append(f"(calendar issue: {', '.join(cerr)})")
    tb, nb = trump_block(24), news_block(hours=24)
    msg += [""] + tb + [""] + nb
    big = any(tmr.strftime("%a %d %b") in l and ("FOMC" in l or "CPI" in l or "NFP" in l) for l in cal)
    q.push("Nasdaq: events & news" + (" - BIG EVENT TOMORROW" if big else ""), clip("\n".join(msg)),
           priority="high" if big else "default", tags="newspaper")
    write_status(events=["NEXT 5 TRADING DAYS:"] + cal, news=nb, trump=tb)
    try:
        pb = event_playbook.lines(tmr, nq)
        if pb:
            q.push(f"Event playbook for {tmr:%a %d %b}", clip("\n".join(pb)), priority="high", tags="warning")
        write_status(playbook=pb or [f"No FOMC, CPI or jobs report on {tmr:%a %d %b}."])
    except Exception as e:
        print("playbook failed:", e)

    run_forecast(ts, S, text, tmr)
    try:
        write_status(recap=recap.weekly(DAILY_LOG, SPOTS, analyst.TRADING_DAY, ts))
    except Exception:
        pass

    if (tmr - ts.date()).days > 1:                     # last session of the week -> weekly recap
        try:
            rl = recap.weekly(DAILY_LOG, SPOTS, analyst.TRADING_DAY, ts)
            q.push("Weekly recap", clip("\n".join(rl)), priority="default", tags="bar_chart")
        except Exception as e:
            q.push("Weekly recap failed", f"{type(e).__name__}: {e}", priority="low", tags="warning")


def morning():
    today = lux_today()
    if today.weekday() >= 5:
        return
    cal, cerr = events.calendar_block(today, days=1)
    hours = 64 if today.weekday() == 0 else 16       # Monday: include the weekend
    try:
        h = pd.read_csv(q.HIST, parse_dates=["date"]).sort_values("date")
        r = float((h.gexn.iloc[-1] > h.gexn.iloc[:-1].tail(252).to_numpy(float)).mean())
        qn = min(5, int(r * 5) + 1)
    except Exception:
        qn = None
    level, acts = playbook.advise(qn, events.macro_events(today), truth.hot(16), _after_close(today))
    msg = playbook.render(level, acts)
    try:
        snap = json.load(open(STATUS))
    except Exception:
        snap = {}
    fresh = snap.get("for") == f"{today:%a %d %b}"      # evening snapshot was made for today
    if not fresh:
        snap = {}
    if snap.get("range"):
        msg += ["", "EXPECTED RANGE TODAY:"] + snap["range"]
    if snap.get("walls"):
        msg += ["", "GAMMA WALLS:"] + [l for l in snap["walls"] if l]
    write_status(**{"for": f"{today:%a %d %b}", "advice": playbook.render(level, acts), "level": level})
    msg += ["", "TODAY:"] + cal
    if cerr:
        msg.append(f"(calendar issue: {', '.join(cerr)})")
    tb, nb = trump_block(hours), news_block(hours=hours, top=6)
    msg += ["", last_qqq_reading(), ""] + tb + [""] + nb
    write_status(news=nb, trump=tb, today=["TODAY:"] + cal)
    try:
        bp = (json.load(open(STATUS)).get("brain_pred") or {})
        pb = event_playbook.lines(today, float(bp.get("nq") or 0) or nq_level(float(pd.read_csv(SPOTS).spot.iloc[-1])))
        if pb:                                       # right after today's calendar, before news (news may get clipped)
            i = msg.index("TODAY:") + 1 + len(cal) if "TODAY:" in msg else len(msg)
            msg[i:i] = [""] + pb
    except Exception as e:
        print("playbook failed:", e)
    big = any(("FOMC" in l or "CPI" in l or "NFP" in l) for l in cal)
    q.push(f"Today: risk {level}" + (" - BIG EVENT" if big else ""), clip("\n".join(msg)),
           priority="high" if (big or level in ("ELEVATED", "HIGH")) else "default", tags="sunrise")


def test():
    print("== QQQ chain");
    try:
        ts, d = q.load_chain(None); S = q.spot_by_parity(d)
        print(f"  ok: {len(d)} contracts, date {ts.date()}, spot {S:.2f}, gamma ratio {q.gamma_sanity(d, S)}")
    except Exception as e:
        print("  FAILED", e); d = None
    print("== NDX chain")
    try:
        t2, d2 = ndx.parse(ndx.fetch()); S2 = ndx.spot_by_parity(d2)
        print(f"  ok: {len(d2)} contracts, date {t2.date()}, spot {S2:.2f}, "
              f"OI>0 rows {(d2.open_interest>0).sum()}, gamma>0 rows {(d2.gamma>0).sum()}, "
              f"gamma ratio {ndx.gamma_ratio(d2, S2)}")
    except Exception as e:
        print("  FAILED", e)
    print("== Earnings calendar")
    e, err = events.earnings_for(next_trading_day(lux_today()))
    print("  ", err or f"ok ({e or 'no megacaps that day'})")
    print("== News feeds")
    items, status = news.fetch_all()
    for k, v in status.items():
        print(f"  {k:26} {v}")
    print("== Truth Social (Trump)")
    try:
        posts = truth.fetch()
        rel = [p for p in posts if truth.relevance(p["text"])]
        print(f"  ok ({len(posts)} posts, {len(rel)} market-relevant); newest: {posts[0]['ts']}")
    except Exception as e:
        print("  FAILED", e)
    print("== Claude (news ranking + forecast):", "key set" if cfg().get("anthropic_api_key") else "no key - forecast and Claude ranking are off")
    q.push("Nasdaq bot: test", "If you see this, notifications work.", tags="white_check_mark")
    print("== test message sent - check your Discord channel")


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "--evening").lower()
    force = "--force" in sys.argv
    if mode in ("--evening", "--morning") and not force and not cloud_should_run(mode):
        sys.exit(0)
    try:
        if mode == "--test":
            test()
        elif mode == "--brainping":
            print("brain webhook set:", bool(BRAIN_HOOK))
            q.push("BRAIN online", "Hi, I'm Volta's brain. 2,948 market days in memory.\n"
                   "From Monday after the US close I post tomorrow's NQ range forecast here, "
                   "the past days that look most like today, and a journal grading my own calls.",
                   tags="brain", hook=BRAIN_HOOK or None)
        elif mode == "--nerdping":
            print("nerd webhook set:", bool(NERD_HOOK))
            q.push("Options nerd online", "Every evening after the US close: dealer greeks, vol surface, skew, "
                   "implied moves per expiry and max pain for QQQ - each with what it means. Ask anytime with /nerd.",
                   tags="nerd", hook=NERD_HOOK or None)
        elif mode == "--nerdlive":                       # intraday refresh of /nerd (no Discord post, history untouched)
            from zoneinfo import ZoneInfo
            ts, d = q.load_chain(None)
            live = d[(d.dte >= 0) & (d.dte <= 45) & (d.bid > 0) & (d.ask > 0)]
            if len(live) < 200:                          # outside US hours CBOE clears the quotes
                print(f"no live quotes ({len(live)} quoted contracts) - market closed, keeping the last read")
                sys.exit(0)
            S = q.spot_by_parity(d)
            try:
                c = brain.yahoo("QQQ").close; rv20 = float(np.log(c).diff().tail(20).std() * np.sqrt(252))
            except Exception:
                rv20 = None
            lines = options_nerd.read(d, S, ts, rv20=rv20, nq_ratio=nq_level(S) / S, write=False)
            ny = datetime.now(ZoneInfo("America/New_York")); lux = datetime.now(ZoneInfo("Europe/Luxembourg"))
            head = [f"LIVE options read - {lux:%a %d %b %H:%M} Lux ({ny:%H:%M} NY), quotes ~15 min delayed, QQQ {S:.2f}", ""]
            st = json.load(open(STATUS))
            st["nerd"] = head + lines
            json.dump(st, open(STATUS, "w"), indent=1)              # leaves the briefing's 'updated' time alone
            print("\n".join(head + lines[:6]))
        elif mode == "--relevel":                        # one-off: put today's /range and /walls on NQ-futures prices
            import re
            st = json.load(open(STATUS)); b = nq_basis(); print("NQ futures / NDX basis:", round(b, 5))
            txt = " ".join(st.get("range") or [])
            m = re.search(r"±(\d+) pt move in NQ \(([\d.]+)%\).*?±(\d+) pts -> roughly ([\d,]+) to ([\d,]+).*?~(\d+)% of such", txt)
            if m and "CLOSE-TO-CLOSE" not in txt:
                A, P, T = float(m[1]), float(m[2]), float(m[3]); lo, hi = (float(x.replace(",", "")) for x in (m[4], m[5]))
                r = {"implied_pts": A * b, "implied_pct": P, "typical_pts": T * b, "typical_pct": P * T / A, "nq": (lo + hi) / 2 * b,
                     "ratio": 1.0 if "about right" in txt else 0.8, "inside": float(m[6]) / 100}
                st["range"] = levels.range_lines(r)
            ts, d = q.load_chain(None); S = q.spot_by_parity(d)
            run_ndx(ts, d, S, write=False); nq = nq_level(S)
            chains = [(d, S, nq / S)] + ([(_NDX["d"], _NDX["S"], nq_basis())] if "d" in _NDX else [])
            st["walls"] = levels.wall_lines(levels.walls(chains, nq), nq, S / nq)
            json.dump(st, open(STATUS, "w"), indent=1)
            print("\n".join(st["range"] + [""] + st["walls"]))
        elif mode == "--nerd":                           # dry run of the options-nerd read
            ts, d = q.load_chain(None); S = q.spot_by_parity(d)
            nerd_step(d, S, ts, nq_level(S), dry=True)
        elif mode == "--brain":                          # dry run: print the brain's reading, write nothing
            ts, d = q.load_chain(None); S = q.spot_by_parity(d)
            h = pd.read_csv(q.HIST).sort_values("date")
            r = float((h.gexn.iloc[-1] > h.gexn.iloc[:-1].tail(252).to_numpy(float)).mean())
            qn = min(5, int(r * 5) + 1)
            rng = levels.expected_range(d, S, ts, qn, nq_level(S))
            brain_step(d, S, ts, f"rank vs last 252 days: {r:.2f}", qn, rng, nq_level(S), dry=True)
        elif mode == "--morning":
            morning()
            _mark("morning", lux_today().isoformat())
        elif mode == "--trump":
            try:                                         # runs every 5 min: never spam error pushes
                truth.watch(TRUTH_SEEN, q.push)
                write_status(trump=trump_block(24))
            except Exception as e:
                with open(os.path.join(HERE, "trump_errors.log"), "a") as f:
                    f.write(f"{datetime.now():%Y-%m-%d %H:%M} {type(e).__name__}: {e}\n")
        else:
            files = [a for a in sys.argv[2:] if not a.startswith("--")]   # optional offline chain files
            evening(*(files + [None, None])[:2])
            if not files:
                _mark("evening", _expected_session())
    except Exception:
        q.push("Nasdaq bot ERROR", traceback.format_exc()[-1500:], priority="high", tags="warning")
        raise
