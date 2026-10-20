"""
trump_watch.py - lightweight Truth Social watcher (standard library only, no pandas),
so the frequent cloud job starts in seconds. Same behaviour as `nasdaq_bot.py --trump`.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import truth

STATUS = os.path.join(HERE, "status.json")
SEEN = os.path.join(HERE, "truth_seen.json")
HOOK = os.environ.get("DISCORD_WEBHOOK", "")
COLORS = {"urgent": 0xE03131, "high": 0xF08C00, "default": 0x1C7ED6, "low": 0x868E96}


def push(title, body, priority="default", tags=""):
    if not HOOK:
        print("[no DISCORD_WEBHOOK - would push]", title); return
    embed = {"title": ("🚨 " + title)[:256], "description": (body or "(empty)")[:4000],
             "color": COLORS.get(priority, COLORS["default"])}
    data = json.dumps({"username": "Volta", "embeds": [embed],
                       "allowed_mentions": {"parse": []}}).encode("utf-8")
    req = urllib.request.Request(HOOK, data=data, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "DiscordBot (Volta, 1.0)"})
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30).read(); break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + attempt * 2); continue
            print("push failed:", e); break
        except Exception as e:
            print("push failed:", e); break
    time.sleep(1)


def trump_block(hours):
    lines, err = truth.digest(hours=hours)
    head = [f"TRUMP on Truth Social (market-relevant, last {hours}h):"]
    if err:
        return head + [f"  ({err})"]
    return head + (lines or ["- nothing market-relevant"])


def write_status(key, value):
    try:
        old = json.load(open(STATUS))
    except Exception:
        old = {}
    if json.loads(json.dumps(value, default=str)) == old.get(key):
        return
    old[key] = value
    try:
        from zoneinfo import ZoneInfo
        old["updated"] = datetime.now(ZoneInfo("Europe/Luxembourg")).strftime("%a %d %b %H:%M Lux")
    except Exception:
        pass
    json.dump(json.loads(json.dumps(old, default=str)), open(STATUS, "w"), indent=1)


if __name__ == "__main__":
    try:
        truth.watch(SEEN, push)
        write_status("trump", trump_block(24))
    except Exception as e:
        with open(os.path.join(HERE, "trump_errors.log"), "a") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M} {type(e).__name__}: {e}\n")
