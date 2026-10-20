"""
recap.py - daily log of what the bot said, and the Friday weekly recap that checks it
against what QQQ actually did. This is the live validation of the gamma signal.
"""
import os
import numpy as np
import pandas as pd

COLS = ["date", "rank", "quintile", "implied_pct", "typical_pct", "risk", "nq"]


def log_day(path, date, rank, quintile, rng, risk):
    h = pd.read_csv(path, parse_dates=["date"]) if os.path.exists(path) else pd.DataFrame(columns=COLS)
    h = h[h.date != pd.Timestamp(date)]
    row = {"date": pd.Timestamp(date), "rank": round(rank, 3) if rank == rank else None, "quintile": quintile,
           "implied_pct": round(rng["implied_pct"], 3) if rng else None,
           "typical_pct": round(rng["typical_pct"], 3) if rng else None,
           "risk": risk, "nq": round(rng["nq"], 1) if rng else None}
    h = pd.concat([h, pd.DataFrame([row])])
    h["date"] = pd.to_datetime(h["date"])
    h = h.sort_values("date")
    h.to_csv(path, index=False, date_format="%Y-%m-%d")
    return h


def _joined(log_path, closes_path, trading_day):
    if not (os.path.exists(log_path) and os.path.exists(closes_path)):
        return None
    h = pd.read_csv(log_path, parse_dates=["date"])
    s = pd.read_csv(closes_path, parse_dates=["date"]).drop_duplicates("date").set_index("date").spot
    out = []
    for r in h.itertuples():
        nxt = r.date + trading_day
        if r.date in s.index and nxt in s.index:
            mv = (s[nxt] / s[r.date] - 1) * 100
            out.append(dict(date=r.date, next=nxt, quintile=r.quintile, implied=r.implied_pct,
                            typical=r.typical_pct, risk=r.risk, move=mv))
    return pd.DataFrame(out)


def weekly(log_path, closes_path, trading_day, today):
    j = _joined(log_path, closes_path, trading_day)
    if j is None or j.empty:
        return ["No graded days yet - the first recap needs a week of logged readings."]
    wk = j[j.next > pd.Timestamp(today) - pd.Timedelta(days=7)]
    lines = ["THIS WEEK - what the bot said vs what QQQ did next day:"]
    for r in wk.itertuples():
        inside = "inside" if r.implied == r.implied and abs(r.move) <= r.implied else "OUTSIDE"
        q = f"q{int(r.quintile)}" if r.quintile == r.quintile else "q?"
        imp = f"±{r.implied:.2f}%" if r.implied == r.implied else "n/a"
        lines.append(f"  {r.date:%a %d %b}: {r.risk}, gamma {q}, priced {imp} -> moved {r.move:+.2f}% ({inside})")
    lines.append("")
    lines.append(f"LIVE TALLY since start ({len(j)} days):")
    lo = j[j.quintile.isin([1, 2])].move.abs(); hi = j[j.quintile.isin([4, 5])].move.abs()
    if len(lo) and len(hi):
        lines.append(f"  low-gamma days avg move {lo.mean():.2f}% (n={len(lo)}) vs high-gamma {hi.mean():.2f}% (n={len(hi)})")
        verdict = ("as expected (low gamma = bigger moves)" if lo.mean() > hi.mean() else
                   "NOT as expected so far")
        lines.append(f"  -> {verdict}" + ("" if min(len(lo), len(hi)) >= 20 else " - still too few days to judge"))
    else:
        lines.append("  need both low- and high-gamma days to compare")
    ok = j.dropna(subset=["implied"])
    if len(ok):
        lines.append(f"  stayed inside the options-priced move: {(ok.move.abs() <= ok.implied).mean():.0%} "
                     f"of days (backtest: ~55-70%)")
    return lines
