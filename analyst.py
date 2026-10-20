"""
analyst.py - Claude reads the day's market-relevant news, Trump posts, upcoming
events and the gamma reading, and makes a DIRECTIONAL forecast for the Nasdaq:
P(QQQ up next session) and P(up over 5 sessions).

EXPERIMENTAL AND UNPROVEN. It cannot be backtested honestly (the model already
knows how past markets moved), so it is tested FORWARD: every forecast is logged
before the outcome exists and scored automatically against what QQQ actually did,
versus the dumb benchmark "always say up". Do not trade on it until the scorecard
beats that benchmark over ~200 forecasts.

Needs an Anthropic API key in config.json ("anthropic_api_key").
"""
import json, os, re, urllib.request
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd

MODEL = "claude-sonnet-5-5"
BASE_UP = 0.54          # share of up days for QQQ/NQ over long samples (approx.)

# NYSE full-day holidays (update yearly) -> exact "next trading day" for grading
NYSE_HOLIDAYS = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
                 "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
                 "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
                 "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"]
TRADING_DAY = pd.offsets.CustomBusinessDay(holidays=NYSE_HOLIDAYS)


def _call_claude(key, prompt, max_tokens=1500):
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=120))
    return "".join(c.get("text", "") for c in out["content"] if c.get("type") == "text")


def build_prompt(date_str, spot, recent, headlines, trump, events_lines, gamma_line):
    rec = ", ".join(f"{d}: {s:.2f}" for d, s in recent) or "n/a"
    return f"""You are a macro and tech-sector analyst writing a short forecast for a Nasdaq-100 futures trader.
Date (after the US close): {date_str}. QQQ close: {spot:.2f}. Recent QQQ closes: {rec}.

Dealer gamma: {gamma_line}
(Gamma predicts the SIZE of tomorrow's moves, not their direction. Do not use it for direction.)

Upcoming scheduled events:
{chr(10).join(events_lines) or '- none'}

Trump's market-relevant Truth Social posts, last 24h:
{chr(10).join(trump) or '- none'}

Market-relevant headlines, last 24h (source in brackets):
{chr(10).join(headlines) or '- none'}

Task: estimate the probability that QQQ closes HIGHER at the next session's close than today's close,
and higher 5 sessions from now. Rules:
- The long-run base rate of an up day is about {BASE_UP:.0%}. Most news is priced in within minutes, so
  stay close to the base rate unless something is genuinely new, large and not yet digested
  (e.g. after-hours megacap earnings, policy shocks, export-control changes, chip supply news).
- Probabilities outside 0.35-0.70 should be rare. Be calibrated, not dramatic.
- Separate signal from noise; say briefly why the main drivers matter for the Nasdaq-100 specifically.
- Mention what would prove the call wrong.

Reply ONLY with JSON:
{{"p_up_1d": <0-1>, "p_up_5d": <0-1>, "drivers": ["<max 20 words>", "... up to 3"],
  "against": "<max 25 words: what would make this wrong>", "confidence": "low|medium|high"}}"""


def forecast(key, **kw):
    txt = _call_claude(key, build_prompt(**kw))
    j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    j["p_up_1d"] = float(np.clip(float(j["p_up_1d"]), 0.01, 0.99))
    j["p_up_5d"] = float(np.clip(float(j["p_up_5d"]), 0.01, 0.99))
    return j


# ------------------------------------------------------------------ logging & scoring
def log_spot(path, date, spot):
    s = pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame(columns=["date", "spot"])
    s = s[s.date != pd.Timestamp(date)]
    s = pd.concat([s, pd.DataFrame([{"date": pd.Timestamp(date), "spot": round(float(spot), 2)}])]).sort_values("date")
    s.to_csv(path, index=False, date_format="%Y-%m-%d")
    return s


def recent_closes(spots, n=5):
    t = spots.tail(n + 1).iloc[:-1]
    return [(d.strftime("%a %d %b"), v) for d, v in zip(t.date, t.spot)]


def log_prediction(path, date, spot, j):
    p = pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame()
    row = {"date": pd.Timestamp(date), "spot": round(float(spot), 2), "p_up_1d": j["p_up_1d"],
           "p_up_5d": j["p_up_5d"], "confidence": j.get("confidence", ""),
           "drivers": " | ".join(j.get("drivers", []))[:500], "model": MODEL}
    if not p.empty:
        p = p[p.date != row["date"]]
    p = pd.concat([p, pd.DataFrame([row])]).sort_values("date")
    p.to_csv(path, index=False, date_format="%Y-%m-%d")


def scorecard(pred_path, spot_path):
    """Grades every forecast whose outcome is known. Returns text lines."""
    if not (os.path.exists(pred_path) and os.path.exists(spot_path)):
        return ["Scorecard: no graded forecasts yet."]
    p = pd.read_csv(pred_path, parse_dates=["date"])
    s = pd.read_csv(spot_path, parse_dates=["date"]).drop_duplicates("date").set_index("date").spot
    late = p.get("model", pd.Series("", index=p.index)).astype(str).str.endswith("-late")
    n_late = int(late.sum())
    p = p[~late]                                   # late (morning-after) forecasts are never graded
    rows = []
    for r in p.itertuples():
        if r.date not in s.index:
            continue
        d1 = r.date + TRADING_DAY
        d5 = r.date + 5 * TRADING_DAY
        o1 = bool(s[d1] > s[r.date]) if d1 in s.index else None   # missing close -> not graded
        o5 = bool(s[d5] > s[r.date]) if d5 in s.index else None
        rows.append((r.p_up_1d, o1, r.p_up_5d, o5))
    g1 = [(pp, o) for pp, o, _, _ in rows if o is not None]
    g5 = [(pp, o) for _, _, pp, o in rows if o is not None]
    if not g1:
        return ["Scorecard: no graded forecasts yet (first grades arrive the evening after the first forecast)."]
    out = []
    for lab, g in [("next day", g1), ("5 days", g5)]:
        if not g:
            continue
        pp = np.array([a for a, _ in g]); oo = np.array([b for _, b in g], dtype=float)
        hit = np.mean((pp > 0.5) == (oo == 1))
        always_up = oo.mean()
        brier = np.mean((pp - oo) ** 2); brier_base = np.mean((BASE_UP - oo) ** 2)
        out.append(f"  {lab}: n={len(g)}, right {hit:.0%} vs 'always up' {always_up:.0%}; "
                   f"Brier {brier:.3f} vs base {brier_base:.3f} (lower is better)")
    # Sequential test: checked every evening, so early verdicts need much stronger evidence
    # (t > 3 before 200 days, t > 2 at 200+). Measured on BOTH Brier score (calibration) and
    # hit rate vs "always up". A strong edge proves itself in ~60-80 days.
    n = len(g1)
    pp = np.array([a for a, _ in g1]); oo = np.array([b for _, b in g1], dtype=float)
    if n >= 20:
        d = (BASE_UP - oo) ** 2 - (pp - oo) ** 2
        t_b = d.mean() / (d.std(ddof=1) / np.sqrt(n)) if d.std(ddof=1) > 0 else 0.0
        hits = ((pp > 0.5) == (oo == 1)).astype(float)
        base = np.maximum(oo.mean(), 1 - oo.mean())          # best constant guess in hindsight
        t_h = (hits.mean() - base) / (hits.std(ddof=1) / np.sqrt(n)) if hits.std(ddof=1) > 0 else 0.0
    else:
        t_b = t_h = 0.0
    need = 3.0 if n < 200 else 2.0
    if n >= 60 and t_b > need and t_h > need:
        verdict = f"PROVEN EDGE (t={t_b:.1f} / {t_h:.1f} over {n} days) - usable as a directional input"
    elif (n >= 200 and (t_b < 1 or t_h < 1)) or n >= 300:
        verdict = f"NO EDGE after {n} days (t={t_b:.1f} / {t_h:.1f}) - forecaster retired"
    else:
        verdict = (f"UNPROVEN - {n} graded days, evidence t={t_b:.1f} / {t_h:.1f} "
                   f"(needs >{need:.0f} on both; a real edge usually shows within 60-80 days). Don't trade on it yet.")
    extra = [f"  ({n_late} late forecasts shown but not graded)"] if n_late else []
    return ["Scorecard:"] + out + extra + [f"  Verdict: {verdict}"]
