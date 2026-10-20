"""Registers Volta's slash commands in every server the bot is in (run once via the
'register-discord' GitHub workflow). Also clears any old global commands."""
import json, os, urllib.request

TOKEN, APP = os.environ["DISCORD_TOKEN"], os.environ["DISCORD_APP_ID"]
API = "https://discord.com/api/v10"
COMMANDS = [
    ("status", "Risk level, what to do, gamma"), ("range", "Where NQ likely closes + full-day high-low range (NQ futures prices)"),
    ("walls", "Gamma walls and flip in NQ futures prices (tested: not support/resistance)"), ("events", "Scheduled events, next 5 trading days"),
    ("earnings", "Big-tech earnings & priced moves"), ("news", "Latest filtered headlines"),
    ("trump", "Trump's market-relevant posts, last 24h"), ("recap", "This week: readings vs actual moves"),
    ("forecast", "Latest experimental forecast + scorecard"), ("brain", "The brain: tomorrow's range, high/low, similar days, live score"), ("nerd", "Options nerd: dealer greeks, vol surface, skew, implied moves"), ("help", "List the commands"),
    ("ask", "Ask Volta about today's market read"),
    ("odds", "Your stop & target: how often each got hit first on days like tomorrow"),
    ("learning", "What Volta has been reading and which ideas it tested"),
    ("live", "During the US session: range so far, updated forecast, what's usually left"),
    ("playbook", "What NQ historically does on the next FOMC / CPI / jobs day"),
    ("plan", "Today's size and loss limits for your account (buffer = distance to max-loss limit)"),
    ("wishes", "Volta's self-check: its diary and what it needs to get better"),
    ("book", "Volta as a trader: its virtual prop account, trades and journal"),
    ("strategies", "Strategy lab: what Volta built and tested, what passed, live results"),
    ("powers", "Open read: odds for yesterday's high/low, gap fill, tail day, Asia/London"),
    ("shortvol", "Today's short-vol check: paper iron fly on high-gamma days + live score"),
]
OPTIONS = {"plan": [{"name": "buffer", "description": "Dollars left to your max-loss limit, e.g. 1000", "type": 10, "required": True, "min_value": 50},
                    {"name": "stop", "description": "Your stop in NQ points (optional)", "type": 10, "required": False, "min_value": 2},
                    {"name": "contract", "description": "MNQ (default) or NQ", "type": 3, "required": False,
                     "choices": [{"name": "MNQ", "value": "MNQ"}, {"name": "NQ", "value": "NQ"}]}],
           "ask": [{"name": "question", "description": "Your question", "type": 3, "required": True, "max_length": 500}],
           "odds": [{"name": "stop", "description": "Stop distance in NQ points", "type": 10, "required": True, "min_value": 1},
                    {"name": "target", "description": "Target distance in NQ points", "type": 10, "required": True, "min_value": 1},
                    {"name": "side", "description": "long or short", "type": 3, "required": True,
                     "choices": [{"name": "long", "value": "long"}, {"name": "short", "value": "short"}]},
                    {"name": "entry", "description": "Entry at the open, or anytime in the session (default)", "type": 3,
                     "required": False, "choices": [{"name": "anytime", "value": "any"}, {"name": "at the open", "value": "open"}]}]}


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json",
                                          "User-Agent": "nasdaq-bot (github actions, 1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


cmds = [{"name": n, "description": d, "type": 1, **({"options": OPTIONS[n]} if n in OPTIONS else {})}
        for n, d in COMMANDS]
call("PUT", f"/applications/{APP}/commands", [])                     # clear global commands
guilds = call("GET", "/users/@me/guilds")
for g in guilds:
    call("PUT", f"/applications/{APP}/guilds/{g['id']}/commands", cmds)
    print(f"registered {len(cmds)} commands in server '{g['name']}'")
if not guilds:
    print("The bot is in no server yet - invite it first, then run this again.")
