"""
Donald Trump's Truth Social posts, via the public archive feed at trumpstruth.org
(Truth Social itself has no open feed). Only market-relevant posts pass the filter:
tariffs/trade, China/Taiwan, the Fed/rates, chips/tech companies, oil/war/sanctions,
the stock market. Endorsements, rallies and political attacks are dropped.

Used two ways:
  - digest():  market-relevant posts of the last N hours for the morning/evening push
  - watch():   run every few minutes; pushes NEW market-relevant posts immediately
"""
import json, os, re, html, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

URL = "https://trumpstruth.org/feed"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36"}

MARKET = [
    (r"\btariffs?\b|\bduties\b|\btrade (deal|war|agreement|deficit)\b|\bimport(s|ed)?\b|\bexport(s|ed)?\b", "trade/tariffs"),
    (r"\bchina\b|\bchinese\b|\bxi\b|\btaiwan\b|\bbeijing\b", "China/Taiwan"),
    (r"\bfed\b|\bfederal reserve\b|\bpowell\b|\binterest rates?\b|\brate cuts?\b|\binflation\b", "Fed/rates"),
    (r"\bchips?\b|\bsemiconductors?\b|\bnvidia\b|\bapple\b|\bmicrosoft\b|\bintel\b|\btsmc\b|\bamazon\b|"
     r"\bgoogle\b|\bmeta\b|\btesla\b|\bartificial intelligence\b|\b(the )?ai\b", "tech/chips"),
    (r"\bstock market\b|\bstocks\b|\bdow\b|\bnasdaq\b|\bs&p\b|\bwall street\b|\b401k", "stock market"),
    (r"\boil\b|\bopec\b|\bsanctions?\b|\biran\b|\brussia\b|\bukraine\b|\bwar\b|\bstrikes?\b|\bmilitary\b", "oil/geopolitics"),
    (r"\bexecutive order\b|\bshutdown\b|\bdebt ceiling\b|\bbudget\b|\btax(es)?\b|\btreasury\b|\bdollar\b|\bbonds?\b", "fiscal/policy"),
    (r"\beconomy\b|\bjobs\b|\bgdp\b|\brecession\b|\bmanufacturing\b", "economy"),
]
NOISE = r"complete and total endorsement|has my endorsement|rally\b|vote for|congratulations|happy birthday|rest in peace"


def fetch(timeout=30):
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=timeout).read()
    root = ET.fromstring(raw)
    out = []
    for it in root.iter("item"):
        desc = html.unescape(re.sub(r"<[^>]+>", " ", it.findtext("description") or "")).strip()
        title = html.unescape(it.findtext("title") or "").strip()
        text = re.sub(r"\s+", " ", desc if len(desc) >= len(title.rstrip("…")) else title)
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
        except Exception:
            ts = None
        out.append(dict(id=(it.findtext("link") or text[:80]).strip(), text=text, ts=ts,
                        link=(it.findtext("link") or "").strip()))
    return out


def relevance(text):
    t = text.lower()
    if re.search(NOISE, t) and not re.search(r"tariff|china|fed\b|powell|chip", t):
        return []
    return [lab for rx, lab in MARKET if re.search(rx, t)]


def _lux(ts):
    try:
        from zoneinfo import ZoneInfo
        return ts.astimezone(ZoneInfo("Europe/Luxembourg")).strftime("%a %H:%M")
    except Exception:
        return ts.strftime("%a %H:%M UTC")


def _short(t, n=280):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def digest(hours=24, top=5):
    """Lines for the morning/evening push. Returns (lines, error)."""
    try:
        posts = fetch()
    except Exception as e:
        return [], f"Truth Social feed: {type(e).__name__}"
    cut = datetime.now(timezone.utc) - timedelta(hours=hours)
    rel = [(p, relevance(p["text"])) for p in posts if p["ts"] is None or p["ts"] >= cut]
    rel = [(p, r) for p, r in rel if r][:top]
    return [f"- {_lux(p['ts']) if p['ts'] else ''} [{', '.join(r)}] {_short(p['text'])}" for p, r in rel], None


def hot(hours=18):
    """True if a tariff/China/Fed post appeared in the last `hours`."""
    try:
        cut = datetime.now(timezone.utc) - timedelta(hours=hours)
        return any(set(relevance(p["text"])) & {"trade/tariffs", "China/Taiwan", "Fed/rates"}
                   for p in fetch() if p["ts"] and p["ts"] >= cut)
    except Exception:
        return False


def watch(seen_path, push):
    """Push each NEW market-relevant post once. First run only seeds (no flood)."""
    first = not os.path.exists(seen_path)
    seen = set() if first else set(json.load(open(seen_path)))
    posts = fetch()
    new = [p for p in posts if p["id"] not in seen]
    sent = 0
    if not first:
        for p in reversed(new):                       # oldest first
            r = relevance(p["text"])
            if r and (p["ts"] is None or p["ts"] > datetime.now(timezone.utc) - timedelta(hours=3)):
                import playbook
                push(f"TRUMP: {', '.join(r)}",
                     _short(p["text"], 1200) + "\n\n" + playbook.trump_meaning(r) + f"\n{p['link']}",
                     priority="urgent" if any(x in r for x in ("trade/tariffs", "China/Taiwan", "Fed/rates")) else "high",
                     tags="rotating_light")
                sent += 1
    seen |= {p["id"] for p in posts}
    json.dump(list(seen)[-2000:], open(seen_path, "w"))
    return sent, first
