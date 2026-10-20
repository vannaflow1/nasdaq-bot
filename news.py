"""
News filter: pulls free feeds, keeps only what can move the Nasdaq-100, scores,
de-duplicates and remembers what was already sent.

Scoring = company weight (NDX heavyweights / AI-chip supply chain)
        + topic weight (AI chips & capex, macro & Fed, shocks like probes/bans/guidance).
A headline needs a company OR a macro topic to count.

Optional: set environment variable ANTHROPIC_API_KEY and the top ~25 headlines are
re-ranked by Claude with a one-line "why it matters" each (costs ~1 cent/day).
Without a key the keyword ranking is used.

This is an information filter, NOT a tested trading signal: by the time a headline
is in an RSS feed, the price has usually already reacted.
"""
import json, os, re, time, difflib, html
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

FEEDS = {
    "Yahoo (megacaps)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s="
                        "NVDA,MSFT,AAPL,AMZN,AVGO,META,GOOGL,TSLA,AMD,TSM&region=US&lang=en-US",
    "CNBC tech": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
    "CNBC markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
    "CNBC economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "Tom's Hardware": "https://www.tomshardware.com/feeds/all",
    "The Register": "https://www.theregister.com/headlines.atom",
}

# company -> (weight, regex). Weight ~ importance to NDX moves.
COMPANIES = {
    "NVDA": (5, r"\bnvidia\b|\bnvda\b"), "MSFT": (4, r"\bmicrosoft\b|\bmsft\b"),
    "AAPL": (4, r"\bapple\b|\baapl\b|\biphone\b"), "AMZN": (4, r"\bamazon\b|\bamzn\b|\baws\b"),
    "AVGO": (3, r"\bbroadcom\b|\bavgo\b"), "META": (3, r"\bmeta platforms\b|\bmeta\b(?! description)"),
    "GOOGL": (3, r"\balphabet\b|\bgoogle\b|\bgoogl\b"), "TSLA": (3, r"\btesla\b|\btsla\b"),
    "TSM": (4, r"\btsmc\b|\btaiwan semiconductor\b|\btsm\b"), "AMD": (2, r"\bamd\b|\badvanced micro\b"),
    "ASML": (3, r"\basml\b"), "MU": (2, r"\bmicron\b"), "NFLX": (1, r"\bnetflix\b"),
    "PLTR": (1, r"\bpalantir\b"), "ARM": (1, r"\barm holdings\b"), "INTC": (1, r"\bintel\b"),
    "OPENAI": (2, r"\bopenai\b|\banthropic\b|\bxai\b"),
}
TOPICS = {
    "AI chips/capex": (3, r"\bai chips?\b|\bgpus?\b|\bblackwell\b|\brubin\b|\bhbm\b|\bfoundry\b|\bfab\b|"
                          r"\bwafer|\bdata ?cent(er|re)s?\b|\bcapex\b|\bcapital spending\b|\bhyperscaler"),
    "export/geo": (5, r"export (control|curb|ban|restriction)|\bchina\b.*\bchips?\b|\bsanction|\btaiwan\b|\btariffs?\b"),
    "Fed/macro": (6, r"\bFed\b|\bfomc\b|\bpowell\b|rate (cut|hike)|\binflation\b|\bcpi\b|\bpce\b|"
                     r"\bpayrolls?\b|jobs report|\bunemployment\b|treasury yields?|\brecession\b|\bgdp\b"),
    "shock": (3, r"\bprobe\b|\bantitrust\b|\bban(s|ned)?\b|\bhalt|\brecalls?\b|\bdowngrade|"
                 r"guidance|\bwarns?\b|\bcuts? (forecast|outlook)|\bplunge|\bsoar|\bcrash|\bsell-?off|"
                 r"\bdefault\b|\bbankrupt|\bshutdown\b|\bindictment\b"),
    "earnings": (2, r"\bearnings\b|\bresults\b|\brevenue\b|\bbeats?\b|\bmiss(es)?\b|\bforecast\b"),
}
MACRO_ONLY_OK = {"Fed/macro", "export/geo"}


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_atom(root, source):
    out = []
    for e in root.iter(ATOM + "entry"):
        title = (e.findtext(ATOM + "title") or "").strip()
        ln = e.find(ATOM + "link")
        link = ln.get("href", "") if ln is not None else ""
        pub = e.findtext(ATOM + "updated") or e.findtext(ATOM + "published")
        try:
            ts = datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(timezone.utc) if pub else None
        except Exception:
            ts = None
        if title:
            out.append(dict(title=html.unescape(title), link=link, ts=ts, source=source))
    return out


def _parse_rss(raw, source):
    out = []
    root = ET.fromstring(raw)
    if root.tag == ATOM + "feed":                       # Atom (e.g. Reddit .rss)
        return _parse_atom(root, source)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        try:
            ts = parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None
        except Exception:
            ts = None
        if title:
            out.append(dict(title=html.unescape(title), link=link, ts=ts, source=source))
    return out


def _parse_reddit(raw, source):
    out = []
    for c in json.loads(raw)["data"]["children"]:
        d = c["data"]
        if d.get("stickied"):
            continue
        out.append(dict(title=d["title"], link="https://reddit.com" + d["permalink"],
                        ts=datetime.fromtimestamp(d["created_utc"], timezone.utc),
                        source=source, upvotes=d.get("ups", 0)))
    return out


def fetch_all(feeds=FEEDS):
    items, status = [], {}
    for name, url in feeds.items():
        try:
            raw = _get(url)
            got = _parse_reddit(raw, name) if url.endswith("json") or ".json?" in url else _parse_rss(raw, name)
            items += got
            status[name] = f"ok ({len(got)})"
        except Exception as e:
            status[name] = f"FAILED: {type(e).__name__} {str(e)[:60]}"
        time.sleep(0.5)
    return items, status


def score(item):
    raw = item["title"]
    t = raw.lower()
    comps = [k for k, (w, rx) in COMPANIES.items() if re.search(rx, t)]
    tops = []
    for k, (w, rx) in TOPICS.items():
        # "Fed" must be capitalised (avoids "fed up"); everything else case-insensitive
        rx_ci = rx.replace("\\bFed\\b|", "")
        if re.search(rx_ci, t, flags=re.I) or (k == "Fed/macro" and re.search(r"\bFed\b", raw)):
            tops.append(k)
    if not tops:                      # a company name alone (e.g. "Apple pie") isn't news
        return 0, comps, tops
    if not comps and not (set(tops) & MACRO_ONLY_OK):
        return 0, comps, tops
    s = sum(COMPANIES[c][0] for c in comps) + sum(TOPICS[k][0] for k in tops)
    if item["source"] == "Federal Reserve":
        s += 2 if re.search(r"monetary policy|fomc|statement|minutes", t) else -3
    if item["source"].startswith("Reddit"):
        s = s * 0.5 + min(item.get("upvotes", 0) / 2000, 2)   # forums: noisier, upvotes as tie-break
    return s, comps, tops


def _norm(t):
    t = re.sub(r"[-/]", " ", t.lower())
    t = re.sub(r"[^a-z0-9 ]", "", t)
    syn = {"lifts": "raises", "hikes": "raises", "boosts": "raises", "slashes": "cuts",
           "datacenter": "data center", "datacenters": "data centers"}
    return " ".join(syn.get(w, w) for w in t.split())


def filter_news(items, seen, hours=24, top=8, now=None):
    now = now or datetime.now(timezone.utc)
    cut = now - timedelta(hours=hours)
    cands = []
    for it in items:
        if it["ts"] and it["ts"] < cut:
            continue
        key = _norm(it["title"])
        if key in seen:
            continue
        s, comps, tops = score(it)
        if s >= 4:
            cands.append(dict(it, score=s, comps=comps, topics=tops, key=key))
    cands.sort(key=lambda x: -x["score"])
    picked = []
    for c in cands:                                  # de-duplicate near-identical headlines
        if any(difflib.SequenceMatcher(None, c["key"], p["key"]).ratio() > 0.72 for p in picked):
            continue
        picked.append(c)
    return picked[: max(top * 3, 25)]


def claude_rank(cands, top=8, key=None):
    """Optional re-rank by Claude. Returns list of (index, reason) or None."""
    key = key or os.environ.get("ANTHROPIC_API_KEY")
    if not key or not cands:
        return None
    listing = "\n".join(f"{i}. [{c['source']}] {c['title']}" for i, c in enumerate(cands))
    prompt = (
        "You filter news for a Nasdaq-100 futures trader. From the headlines below, pick at most "
        f"{top} that could plausibly move the Nasdaq-100 or its biggest stocks over the next days "
        "(AI chips and capex, megacap earnings/guidance, Fed/inflation/jobs, export controls, tariffs, "
        "regulation, big shocks). Skip opinion pieces, clickbait, duplicates and stale stories. "
        "Do not predict direction. Reply ONLY with JSON: "
        '[{"i": <index>, "why": "<max 12 words, what it could affect>"}]\n\n' + listing)
    body = json.dumps({"model": "claude-haiku-5-5", "max_tokens": 800,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        txt = json.load(urllib.request.urlopen(req, timeout=60))["content"][0]["text"]
        arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        return [(int(a["i"]), str(a.get("why", ""))) for a in arr if 0 <= int(a["i"]) < len(cands)][:top]
    except Exception:
        return None


def digest(seen_path, hours=24, top=8):
    """Returns (lines, status, ranked_by)."""
    seen = set()
    if os.path.exists(seen_path):
        try:
            seen = set(json.load(open(seen_path)))
        except Exception:
            seen = set()
    items, status = fetch_all()
    cands = filter_news(items, seen, hours=hours, top=top)
    ranked = claude_rank(cands, top=top)
    if ranked:
        chosen = [(cands[i], why) for i, why in ranked]
        by = "Claude"
    else:
        chosen = [(c, ", ".join(c["comps"] + c["topics"])) for c in cands[:top]]
        by = "keywords"
    lines = []
    for c, why in chosen:
        lines.append(f"- {c['title']}  [{c['source']}]" + (f"\n    {why}" if why else ""))
        seen.add(c["key"])
    seen = list(seen)[-3000:]
    json.dump(seen, open(seen_path, "w"))
    return lines, status, by
