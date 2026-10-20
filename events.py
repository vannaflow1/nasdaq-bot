"""
Scheduled market-moving events for the Nasdaq.

Macro dates are copied from the official pages (checked 17 Oct 2026):
  FOMC: federalreserve.gov/monetarypolicy/fomccalendars.htm  (2027 = tentative)
  CPI:  bls.gov/schedule/news_release/cpi.htm
  Jobs: bls.gov/schedule/news_release/empsit.htm
Update these lists once a year. Earnings come live from the Nasdaq calendar API.
"""
import json
import urllib.request
from datetime import date, timedelta

# decision day = second day of each meeting (statement 14:00 NY, presser 14:30)
FOMC = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
        "2026-09-16", "2026-10-28", "2026-12-09",
        "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28",
        "2027-09-15", "2027-10-27", "2027-12-08"]
FOMC_SEP = {"2026-03-18", "2026-06-17", "2026-09-16", "2026-12-09",
            "2027-03-17", "2027-06-09", "2027-09-15", "2027-12-08"}
CPI = ["2026-11-10", "2026-12-10", "2027-01-13", "2027-02-11", "2027-03-10",
       "2027-04-13", "2027-05-12", "2027-06-10", "2027-07-14", "2027-08-11",
       "2027-09-14", "2027-10-14", "2027-11-10", "2027-12-10"]
NFP = ["2026-11-06", "2026-12-04", "2027-01-08", "2027-02-05", "2027-03-05",
       "2027-04-02", "2027-05-07", "2027-06-04", "2027-07-02", "2027-08-06",
       "2027-09-03", "2027-10-08", "2027-11-05", "2027-12-03"]

# Nasdaq-100 heavyweights + key AI-chip suppliers that move them
MEGACAPS = ["NVDA", "MSFT", "AAPL", "AMZN", "AVGO", "META", "GOOGL", "TSLA",
            "NFLX", "COST", "AMD", "PLTR", "ASML", "TSM", "MU", "QCOM", "INTC", "ARM"]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*"}


def lux(day, hh, mm):
    """NY wall-clock time on `day` -> Luxembourg time string (handles the DST-gap weeks)."""
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=ZoneInfo("America/New_York"))
        return t.astimezone(ZoneInfo("Europe/Luxembourg")).strftime("%H:%M")
    except Exception:
        return f"{hh + 6:02d}:{mm:02d}"


def macro_events(day):
    s = day.isoformat()
    out = []
    if s in FOMC:
        out.append(f"FOMC rate decision {lux(day,14,0)} Lux, Powell {lux(day,14,30)}"
                   + (" - with new projections (dot plot)" if s in FOMC_SEP else ""))
    if s in CPI:
        out.append(f"CPI inflation {lux(day,8,30)} Lux")
    if s in NFP:
        out.append(f"Jobs report (NFP) {lux(day,8,30)} Lux")
    return out


def earnings_for(day, timeout=20):
    """Megacap earnings on `day` from the Nasdaq calendar API. Returns (list, error)."""
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={day.isoformat()}"
    try:
        raw = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                               timeout=timeout))
        rows = ((raw.get("data") or {}).get("rows")) or []
    except Exception as e:
        return [], f"nasdaq earnings: {type(e).__name__}"
    out = []
    for r in rows:
        if r.get("symbol") in MEGACAPS:
            t = (r.get("time") or "").replace("time-", "")
            when = {"pre-market": "before open", "after-hours": "after close"}.get(t, "time n/a")
            out.append(f"{r['symbol']} earnings {when}")
    return out, None


def earnings_rows(day):
    """[(symbol, 'before open'|'after close'|'time n/a')] for megacaps reporting on `day`."""
    e, _ = earnings_for(day)
    out = []
    for x in e:
        sym = x.split()[0]
        when = "before open" if "before open" in x else "after close" if "after close" in x else "time n/a"
        out.append((sym, when))
    return out


def next_trading_days(start, n):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def calendar_block(start, days=5, fetch_earnings=True):
    """Text block of events for the next `days` trading days starting at `start`."""
    lines, errors = [], []
    for i, d in enumerate(next_trading_days(start, days)):
        ev = macro_events(d)
        if fetch_earnings:
            e, err = earnings_for(d)
            ev += e
            if err and err not in errors:
                errors.append(err)
        if ev:
            tag = "TODAY" if i == 0 and d == start else d.strftime("%a %d %b")
            lines.append(f"  {tag}: " + "; ".join(ev))
    if not lines:
        lines.append("  no scheduled macro events or megacap earnings")
    return lines, errors


if __name__ == "__main__":
    ls, errs = calendar_block(date.today(), 10)
    print("\n".join(ls)); print("errors:", errs)
