"""redfolder.py - today's red-folder (high-impact USD) events, live, for Volta's news filters.
Source: the free ForexFactory weekly calendar feed (nfs.faireconomy.media). Same columns as the history
(knowledge/data/econ_events_red.csv -> session table): k_red_any, k_red_count, k_red_premarket, k_red_session, k_fomc_day.
Surprises (k_*_surprise) are only filled in history. Any error -> no flags (strategies with news filters then skip)."""
import json, os, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, "knowledge", "redfolder_week.json")
NY = ZoneInfo("America/New_York")
URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def week():
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        json.dump(d, open(CACHE, "w"))
        return d
    except Exception:
        return json.load(open(CACHE)) if os.path.exists(CACHE) else []


def today_flags(day=None):
    day = str(day or datetime.now(NY).date())
    ev = []
    for e in week():
        if e.get("country") != "USD" or str(e.get("impact", "")).lower() != "high": continue
        try:
            t = datetime.fromisoformat(e["date"]).astimezone(NY)
        except Exception:
            continue
        if str(t.date()) == day and t.hour * 60 + t.minute < 16 * 60: ev.append((t, e.get("title", "")))
    pre = [x for x in ev if x[0].hour * 60 + x[0].minute < 9 * 60 + 30]
    return {"k_red_any": float(bool(ev)), "k_red_count": float(len(ev)), "k_red_premarket": float(bool(pre)),
            "k_red_session": float(len(ev) > len(pre)), "k_fomc_day": float(any("fomc" in t.lower() or "federal funds" in t.lower() for _, t in ev)),
            "red_events": [f"{t:%H:%M} ET {n}" for t, n in ev]}


if __name__ == "__main__":
    print(today_flags())
