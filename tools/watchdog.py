"""tools/watchdog.py - tells the owner on Discord when a Volta job has quietly stopped working.

Why (plain words): GitHub sometimes skips scheduled runs, and - worse - a job can finish "green" while the thing it was
supposed to produce never arrives. On 15 Nov 2026 two such cases were found: the prop search had saved nothing for three
weeks (its result files hit GitHub's 100 MB limit) and the evening forward step had crashed every night since 25 Oct.
Every run looked successful. So this watchdog checks two things, once an hour:

  1. RUNS    - did each important workflow have a successful run when it should have?   (GitHub's own run list)
  2. OUTPUTS - did the files that job is supposed to change actually change?            (last commit touching the path)

plus one local check: no tracked file may come close to GitHub's 100 MB limit.

It posts to Discord only when something NEW breaks, once a day while it stays broken, and once when it is fixed.
State (what is currently broken, when it last alerted) lives in knowledge/watchdog_state.json.
Uses only Python's standard library, so it keeps working even if a dependency of the other jobs breaks.

Run:  python tools/watchdog.py            (in the workflow; needs GITHUB_TOKEN and GITHUB_REPOSITORY)
      python tools/watchdog.py --dry      (print what it would say, change nothing, post nothing)
All times below are UTC hours. To add a check, add one line to RUNS or OUTPUTS."""
import json, os, subprocess, sys, urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HERE, "knowledge", "watchdog_state.json")
ALL, WEEK, TUE_SAT = range(7), range(5), range(1, 6)          # Monday = 0
# NYSE full-day holidays (same list as analyst.py - update both every year). On these days the US-session jobs still
# run but have nothing to write, so their OUTPUT checks are skipped.
HOLIDAYS = {"2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
            "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
            "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"}
BIG_FILE_BYTES = 90 * 1024 * 1024

# A rule fires only on its `days`, between `due` and `end` (UTC hours). It then needs proof of life that is either
#   newer than today's `since` hour (daily jobs; negative = yesterday, e.g. -1 = 23:00 yesterday), or
#   at most `every` minutes old (jobs that repeat through the session).
# `market` = the proof depends on a US trading session (skipped on NYSE holidays).
RUNS = [
    # workflow file      label (plain words)                        days     due    end   since / every
    # GitHub runs this "every 5 minutes" job about every 40-90 minutes in practice, with gaps up to ~2.5 hours
    # (16 Nov 2026: a 156-minute gap set off a 2-hour alarm). 4 hours without a run means it is really down.
    ("trump.yml",        "Truth Social watcher",                    ALL,     1.0,  24.0, {"every": 240}),
    ("outlook.yml",      "London outlook (morning)",                WEEK,    8.5,  11.9, {"since": 6.0}),
    ("outlook.yml",      "NY outlook (before the US open)",         WEEK,   15.5,  24.0, {"since": 12.0}),
    ("morning.yml",      "morning briefing",                        WEEK,   15.0,  24.0, {"since": 12.5}),
    ("session.yml",      "live session loop",                       WEEK,   14.0,  21.5, {"every": 120}),
    ("chain-snap.yml",   "option-chain snapshots",                  WEEK,   14.75, 21.0, {"every": 75}),
    ("nerd-live.yml",    "options nerd",                            WEEK,   14.75, 20.5, {"every": 120}),
    ("bias.yml",         "hourly bias check (silent while paused)", WEEK,   15.0,  21.5, {"every": 120}),
    ("volflag.yml",      "short-vol paper trade",                   WEEK,   21.75, 24.0, {"since": 19.5}),
    ("evening.yml",      "evening recap + forward tests",           WEEK,   23.5,  24.0, {"since": 20.5}),
    ("macro.yml",        "daily macro closes",                      WEEK,   23.75, 24.0, {"since": 22.0}),
    ("bar-archive.yml",  "nightly futures bar archive",             TUE_SAT, 2.5,  20.0, {"since": -1.0}),
    ("families.yml",     "family scoring + forward tests",          ALL,    13.0,  24.0, {"since": 4.0}),
    ("prop-search.yml",  "strategy search",                         ALL,     0.0,  24.0, {"every": 600}),
]
OUTPUTS = [
    # path in the repo                 label                                           days     due    end   proof         market
    ("knowledge/prop_search",          "strategy search results (nothing saved)",      ALL,     0.0,  24.0, {"every": 720}, False),
    ("knowledge/eta_history.csv",      "F10/F13 timer",                                ALL,     0.0,  24.0, {"every": 80 * 60}, False),
    ("knowledge/families.json",        "forward-test numbers",                         TUE_SAT, 13.0, 24.0, {"since": 4.0}, True),
    ("knowledge/data/archive",         "futures bar archive files",                    TUE_SAT, 2.5,  20.0, {"since": -1.0}, True),
    ("knowledge/data/chains",          "option-chain snapshot files",                  WEEK,    15.5, 21.0, {"every": 120}, True),
    # 16 Nov 2026: GitHub dropped all six morning tries; one late run "succeeded" at 09:43 Lux without posting.
    ("knowledge/london_today.json",    "London outlook was NOT posted this morning",   WEEK,    8.6,  11.9, {"since": 6.0}, False),
    ("knowledge/bias_log.csv",         "bias log (silent checks)",                     WEEK,    17.0, 24.0, {"since": 13.0}, True),
    ("knowledge/outlook_log.csv",      "NY outlook log",                               WEEK,    15.5, 24.0, {"since": 12.0}, True),
    ("knowledge/level.csv",            "evening run reached its last step",            WEEK,    23.5, 24.0, {"since": 20.5}, True),
]
FAILING = [("tests.yml", "code self-check (tests)")]            # alert when the latest finished run of these FAILED


def applies(days, due, end, now):
    h = now.hour + now.minute / 60
    return now.weekday() in days and due <= h <= end


def threshold(proof, now):
    """Oldest acceptable proof-of-life time for a rule at `now`."""
    if "every" in proof: return now - timedelta(minutes=proof["every"])
    return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=proof["since"])


def is_holiday(now, since_h=0.0):
    """True when the US session the rule refers to fell on an NYSE holiday (rules with a negative `since` look at yesterday)."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    d = (midnight + timedelta(hours=since_h)).date() if since_h < 0 else now.date()
    return d.isoformat() in HOLIDAYS


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def github(path):
    """GET https://api.github.com/repos/<repo>/<path> -> parsed JSON (token from the workflow)."""
    repo = os.environ["GITHUB_REPOSITORY"]; tok = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "volta-watchdog",
                                          **({"Authorization": f"Bearer {tok}"} if tok else {})})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def last_success(fetch, wf):
    r = fetch(f"actions/workflows/{wf}/runs?status=success&per_page=1").get("workflow_runs") or []
    return _parse(r[0]["updated_at"]) if r else None


def last_change(fetch, path):
    r = fetch(f"commits?path={path}&per_page=1")
    return _parse(r[0]["commit"]["committer"]["date"]) if r else None


def latest_failed(fetch, wf):
    r = fetch(f"actions/workflows/{wf}/runs?status=completed&per_page=1").get("workflow_runs") or []
    return bool(r) and r[0].get("conclusion") == "failure"


def big_files(root=HERE):
    try:
        names = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode().split("\0")
    except Exception:
        return []
    out = []
    for n in names:
        p = os.path.join(root, n)
        if "_part" in os.path.basename(n): continue            # parked results files are never written again
        if n and os.path.isfile(p) and os.path.getsize(p) > BIG_FILE_BYTES: out.append((n, os.path.getsize(p) / 1048576))
    return out


def _ago(t, now):
    if t is None: return "never"
    h = (now - t).total_seconds() / 3600
    return f"{h * 60:.0f} min ago" if h < 2 else f"{h:.0f} h ago" if h < 72 else f"{h / 24:.0f} days ago"


def check(now, fetch, root=HERE):
    """-> {id: message} for everything that is wrong right now. A check that cannot be evaluated (API error) is
    reported once as 'watchdog could not check ...' rather than silently passing."""
    bad = {}; cache = {}

    def get(kind, fn, key):
        if (kind, key) not in cache:
            try: cache[(kind, key)] = ("ok", fn(fetch, key))
            except Exception as e: cache[(kind, key)] = ("err", f"{type(e).__name__}: {e}"[:120])
        return cache[(kind, key)]

    for wf, label, days, due, end, proof in RUNS:
        if not applies(days, due, end, now): continue
        st, last = get("run", last_success, wf)
        if st == "err": bad[f"api:{wf}"] = f"Watchdog could not read the run list for {wf} ({last})."; continue
        if last is None or last < threshold(proof, now):
            bad[f"run:{wf}:{label}"] = f"{label} ({wf}): no successful run when one was due - last success {_ago(last, now)}."
    for path, label, days, due, end, proof, market in OUTPUTS:
        if not applies(days, due, end, now): continue
        if market and is_holiday(now, proof.get("since", 0.0)): continue
        st, last = get("out", last_change, path)
        if st == "err": bad[f"api:{path}"] = f"Watchdog could not read the history of {path} ({last})."; continue
        if last is None or last < threshold(proof, now):
            bad[f"out:{path}"] = f"{label}: {path} has not changed when it should have - last change {_ago(last, now)}. The job may be running without saving its results."
    for wf, label in FAILING:
        st, failed = get("fail", latest_failed, wf)
        if st == "ok" and failed: bad[f"fail:{wf}"] = f"{label} ({wf}): the latest run FAILED - a recent code change broke something."
    for n, mb in big_files(root):
        bad[f"big:{n}"] = f"{n} is {mb:.0f} MB - GitHub refuses pushes with files over 100 MB, so the job writing it will stop saving."
    if now.month == 12 and f"{now.year + 1}-01-01" not in HOLIDAYS:
        bad["holidays"] = f"The holiday list in tools/watchdog.py and analyst.py ends in {now.year} - add {now.year + 1}."
    return bad


def decide(bad, state, now):
    """What to post: (new problems, still-open problems for the daily reminder, fixed problems) and the next state."""
    open_ = state.get("open", {}); last_alert = _parse(state.get("last_alert"))
    new = {k: v for k, v in bad.items() if k not in open_}
    fixed = [v["msg"] for k, v in open_.items() if k not in bad]
    still = {k: v for k, v in bad.items() if k in open_}
    remind = bool(still) and (last_alert is None or now - last_alert >= timedelta(hours=24))
    nxt = {"open": {k: {"msg": v, "since": open_.get(k, {}).get("since", now.isoformat(timespec="minutes"))} for k, v in bad.items()},
           "last_alert": now.isoformat(timespec="minutes") if (new or remind) else state.get("last_alert"),
           "last_run": now.isoformat(timespec="minutes")}
    return new, (still if remind else {}), fixed, nxt


def message(new, still, fixed, state_open):
    lines = []
    if new: lines += ["**New:**"] + [f"• {m}" for m in new.values()]
    if still: lines += ["**Still broken:**"] + [f"• {m} (since {state_open.get(k, {}).get('since', '?')} UTC)" for k, m in still.items()]
    if fixed: lines += ["**Back to normal:**"] + [f"• {m.split(':')[0]}" for m in fixed]
    if not lines: return None, None
    title = "🚨 Volta watchdog" if (new or still) else "✅ Volta watchdog - all clear"
    return title, "\n".join(lines)[:3800]


def post(hook, title, body):
    data = json.dumps({"username": "Volta", "embeds": [{"title": title[:256], "description": body, "color": 0xE74C3C if "🚨" in title else 0x2ECC71}],
                       "allowed_mentions": {"parse": []}}).encode("utf-8")
    req = urllib.request.Request(hook, data=data, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "DiscordBot (volta-watchdog, 1.0)"})
    urllib.request.urlopen(req, timeout=30).read()


def main():
    dry = "--dry" in sys.argv; now = datetime.now(timezone.utc)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    bad = check(now, github)
    new, still, fixed, nxt = decide(bad, state, now)
    title, body = message(new, still, fixed, nxt["open"])
    print(f"{now:%Y-%m-%d %H:%M} UTC: {len(bad)} problem(s), {len(new)} new, {len(fixed)} fixed")
    for m in bad.values(): print(" -", m)
    if dry:
        print("(dry run - nothing posted or saved)"); print(title or "", body or ""); return
    hook = os.environ.get("DISCORD_WEBHOOK", "").strip()
    if title and hook:
        try: post(hook, title, body)
        except Exception as e:                                 # could not alert: keep the old state so the alert is retried next hour
            print("Discord post failed:", type(e).__name__, e); nxt["open"] = {k: v for k, v in nxt["open"].items() if k in state.get("open", {})}
            nxt["last_alert"] = state.get("last_alert")
    elif title: print("no DISCORD_WEBHOOK - would post:\n", title, "\n", body)
    json.dump(nxt, open(STATE, "w"), indent=1)


if __name__ == "__main__":
    main()
