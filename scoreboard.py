"""scoreboard.py - one weekly post: every live claim Volta makes, next to what actually happened.

Why (plain words): Volta says many things during a week (a bias, a day-size outlook, "London breaks tend to reverse",
forward tests of the one surviving idea). Each has its own log, and nobody looks at all of them together. This script
reads those logs once a week and writes ONE honest table: what was claimed, how often it was right, how many cases
that is based on. Small samples are labelled as small. Nothing here is a forecast and nothing is tuned.

Sections (each is skipped with a note if its log is missing):
  1. hourly bias               knowledge/bias_log.csv            (paused since 15 Nov 2026, still graded silently)
  2. NY day-size outlook       knowledge/outlook_log.csv  vs the real 08:30-15:00 Chicago range from the bar archive
  3. London breakout tracker   knowledge/london_log.csv
  4. forward tests F10/F12/F13 knowledge/families.json           (the only thing that could become a prop edge)
  5. short-vol paper trade     paper_vol.csv
  6. machine health            knowledge/watchdog_state.json, knowledge/level.csv

Writes status.json["scoreboard"] (Discord: /scoreboard), appends one row a week to knowledge/scoreboard_history.csv and
posts to the briefing channel once per calendar week (Sundays; state in knowledge/scoreboard_state.json).
Run: python scoreboard.py [--dry]      (--dry prints only)"""
import glob, json, os, sys
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATUS = os.path.join(HERE, "status.json")
STATE, HIST = os.path.join(K, "scoreboard_state.json"), os.path.join(K, "scoreboard_history.csv")
SMALL = 30                                   # fewer graded cases than this = "too few to judge"


def _small(n):
    return " (too few to judge)" if n < SMALL else ""


# ---------- 1. bias
def bias_score(L, week_start=None):
    """(right, graded, days) over LONG/SHORT checks that have been graded; optionally only from week_start (YYYY-MM-DD)."""
    a = L[L.bias.isin(["LONG", "SHORT"]) & L.result.isin(["right", "wrong"])]
    if week_start is not None: a = a[a.date.astype(str) >= week_start]
    return int((a.result == "right").sum()), int(len(a)), int(a.date.nunique())


def bias_lines(week_start):
    L = pd.read_csv(os.path.join(K, "bias_log.csv"))
    r, n, d = bias_score(L); rw, nw, _ = bias_score(L, week_start)
    paused = False
    try:
        import bias; paused = bool(getattr(bias, "PAUSED", False))
    except Exception: pass
    if not n: return ["1) Hourly bias: no graded checks yet."], {}
    out = [f"1) Hourly bias{' (PAUSED - still graded silently)' if paused else ''}: {r}/{n} checks right ({r / n:.0%}) over {d} days"
           + (f"; this week {rw}/{nw}" if nw else "; no graded checks this week") + f". The backtest said 54-58%.{_small(n)}"]
    if n >= SMALL: out.append("   Verdict: " + ("worse than a coin flip live - not usable." if r / n < 0.5 else "in line with the backtest so far."))
    return out, {"bias_right": r, "bias_n": n}


# ---------- 2. day-size outlook
def rth_stats(bars):
    """{date: (open, high, low, close)} of the regular session 08:30-15:00 Chicago from 1-minute bars (ts in Chicago time)."""
    b = bars.copy(); m = b.ts.dt.hour * 60 + b.ts.dt.minute
    b = b[(m >= 510) & (m < 900)]; out = {}
    for d, g in b.groupby(b.ts.dt.date):
        if len(g) < 300: continue                               # half days / broken days are not graded
        g = g.sort_values("ts"); out[str(d)] = (float(g.open.iloc[0]), float(g.high.max()), float(g.low.min()), float(g.close.iloc[-1]))
    return out


def load_bars():
    parts = []
    for f in sorted(glob.glob(os.path.join(K, "data", "archive", "NQ_*.csv.gz"))):
        try: parts.append(pd.read_csv(f, parse_dates=["ts"]))
        except Exception as e: print("bar file skipped:", os.path.basename(f), type(e).__name__)
    return pd.concat(parts).drop_duplicates("ts").sort_values("ts") if parts else pd.DataFrame(columns=["ts", "open", "high", "low", "close"])


def outlook_score(O, S):
    """Grades each outlook day that has real bars. -> dict(n, med_err, n_big, big_avg, n_other, other_avg) or None."""
    rows = []
    for r in O.drop_duplicates("date", keep="last").itertuples():
        s = S.get(str(r.date))
        if s is None or not np.isfinite(r.exp_range_pts) or r.exp_range_pts <= 0: continue
        rows.append({"size": r.size, "exp": float(r.exp_range_pts), "act": s[1] - s[2]})
    if not rows: return None
    G = pd.DataFrame(rows); big = G[G["size"].isin(["BUSIER", "WIDE"])]; oth = G[~G["size"].isin(["BUSIER", "WIDE"])]
    return {"n": len(G), "med_err": float((G.act / G.exp - 1).abs().median()),
            "n_big": len(big), "big_avg": float(big.act.mean()) if len(big) else float("nan"),
            "n_other": len(oth), "other_avg": float(oth.act.mean()) if len(oth) else float("nan")}


def outlook_lines():
    O = pd.read_csv(os.path.join(K, "outlook_log.csv")); g = outlook_score(O, rth_stats(load_bars()))
    if not g: return ["2) Day-size outlook: nothing to grade yet."], {}
    out = [f"2) Day-size outlook (NY): {g['n']} days graded. Typical miss of the expected high-low range: {g['med_err']:.0%}."]
    if g["n_big"] and g["n_other"]:
        ok = g["big_avg"] > g["other_avg"]
        out.append(f"   Days called BUSIER/WIDE ({g['n_big']}): real range {g['big_avg']:.0f} pts on average vs {g['other_avg']:.0f} pts on the other "
                   f"{g['n_other']} days - {'bigger, as called' if ok else 'NOT bigger than the rest'}.{_small(g['n'])}")
    else:
        out.append(f"   Not enough different size calls yet to compare big-day calls with the rest.{_small(g['n'])}")
    return out, {"outlook_n": g["n"], "outlook_med_err": round(g["med_err"], 3)}


# ---------- 3. London tracker
def london_score(L):
    f = L[L.faded.astype(str).isin(["yes", "no"])]
    return int((f.faded == "yes").sum()), int(len(f))


def london_lines():
    y, n = london_score(pd.read_csv(os.path.join(K, "london_log.csv")))
    if not n: return ["3) London breakout tracker: no breaks logged yet."], {}
    return [f"3) London breakout tracker: {y}/{n} breaks reversed before the NY open ({y / n:.0%}); in 12 years of history 52-55% did. "
            f"Volta makes no London call from this.{_small(n)}"], {"london_faded": y, "london_n": n}


# ---------- 4. forward tests
def forward_lines(F):
    out = ["4) Forward tests on real futures bars (the only candidates for a prop edge; F10, F12 and F13 share entries = ONE bet):"]; num = {}
    seen = {}
    for f in F:
        fw = f.get("forward") or {}
        if f.get("status") != "forward" or not fw.get("n"): continue
        key = (fw.get("n"), fw.get("edge"))
        if key in seen: seen[key].append(f["id"]); continue       # same trades as an earlier family (F12 inside F10)
        seen[key] = [f["id"]]
    if not seen: return out + ["   no family is in forward test right now."], num
    for f in F:
        fw = f.get("forward") or {}; key = (fw.get("n"), fw.get("edge"))
        if f.get("status") != "forward" or key not in seen or seen[key][0] != f["id"]: continue
        ids = "/".join(seen[key]); left = max(0, 60 - int(fw["n"]))
        out.append(f"   {ids}: {int(fw['n'])} trades, average {fw['edge']:+.2f}R per trade so far (mostly luck at this count). "
                   f"Belief about the true edge: {fw['posterior_mean']:+.3f}R ± {fw['posterior_sd']:.3f}, P(edge > 0) {fw['p_edge_pos']:.0%}. "
                   f"Status {fw.get('decision', '?')}" + (f"; {left} more trades before the eval rule can be asked." if left else "; 60-trade minimum reached."))
        num[f"{f['id'].lower()}_n"] = int(fw["n"]); num[f"{f['id'].lower()}_post"] = fw["posterior_mean"]
    out.append("   Scale (Lucid simulation of 13 Nov 2026): a true edge of +0.03R is worth roughly $30 a month per prop account, "
               "first payout after ~5 months, 18% of accounts reach one.")
    return out, num


# ---------- 5. short-vol paper trade, 6. health
def shortvol_lines():
    p = os.path.join(HERE, "paper_vol.csv")
    if not os.path.exists(p): return ["5) Short-vol paper trade: no trade opened yet (needs a high-gamma day)."]
    L = pd.read_csv(p); done = L[L.status == "closed"] if "status" in L else L.iloc[0:0]
    if done.empty: return [f"5) Short-vol paper trade: {len(L)} opened, none closed yet."]
    return [f"5) Short-vol paper trade: {len(done)} closed, {(done.pnl > 0).mean():.0%} wins, average {done.pnl_bp.mean():+.1f} bp "
            f"(backtest +8.1 bp, 58% wins).{_small(len(done))}"]


def health_lines(now):
    out = []
    try:
        lv = pd.read_csv(os.path.join(K, "level.csv")).iloc[-1]
        out.append(f"6) Strategy search: {int(lv.searched):,} strategies tested in total (leaderboard and luck bar: /search).")
    except Exception: out.append("6) Strategy search: count unavailable.")
    try:
        w = json.load(open(os.path.join(K, "watchdog_state.json"))); op = w.get("open", {})
        last = datetime.fromisoformat(w["last_run"]); age = (now - last).total_seconds() / 3600
        out.append(f"   Machine health: watchdog last ran {age:.0f} h ago" + (" (TOO LONG AGO - the watchdog itself may be down)" if age > 6 else "")
                   + (f"; {len(op)} open problem(s): " + "; ".join(v["msg"].split(":")[0] for v in op.values()) if op else "; no open problems") + ".")
    except Exception:
        out.append("   Machine health: the watchdog has not reported yet.")
    return out


def build(now=None):
    now = now or datetime.now(timezone.utc)
    week_start = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    lines = [f"📋 VOLTA WEEKLY SCOREBOARD - week to {now:%a %d %b %Y}", "Every live claim next to what actually happened. No forecasts, no spin."]
    num = {"date": now.strftime("%Y-%m-%d")}
    for fn in (lambda: bias_lines(week_start), outlook_lines, london_lines,
               lambda: forward_lines(json.load(open(os.path.join(K, "families.json"))))):
        try:
            L, n = fn(); lines += L; num.update(n)
        except Exception as e:
            lines.append(f"(a section could not be read: {type(e).__name__}: {str(e)[:80]})")
    for fn in (shortvol_lines, lambda: health_lines(now)):
        try: lines += fn()
        except Exception as e: lines.append(f"(a section could not be read: {type(e).__name__}: {str(e)[:80]})")
    if len("\n".join(lines)) > 1950:                           # Discord replies are cut at ~2000 characters: drop the context line first
        lines = [x for x in lines if not x.startswith("   Scale (")]
    return lines, num


def main():
    dry = "--dry" in sys.argv; now = datetime.now(timezone.utc)
    lines, num = build(now)
    print("\n".join(lines))
    if dry: return
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    s["scoreboard"] = lines; json.dump(s, open(STATUS, "w"), indent=1)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    week = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    if st.get("posted") == week or (now.weekday() != 6 and "--post" not in sys.argv):
        print("status updated; weekly post already sent or not Sunday"); return
    H = pd.read_csv(HIST) if os.path.exists(HIST) else pd.DataFrame()
    pd.concat([H, pd.DataFrame([num])], ignore_index=True).to_csv(HIST, index=False)
    import qqq_gex_daily as q
    q.push("Weekly scoreboard", "\n".join(lines[1:]), hook=os.environ.get("DISCORD_WEBHOOK") or None)
    st["posted"] = week; json.dump(st, open(STATE, "w"), indent=1)


if __name__ == "__main__":
    main()
