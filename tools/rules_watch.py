"""tools/rules_watch.py - weekly watcher of the prop firms' OFFICIAL rule pages (expert review, upgrade 9a).

Volta's simulator rules come partly from third-party guides. This job fetches each firm's official pages, reduces them to
plain text, and compares a hash with last week's. A change -> a Discord note and a wish for Claude to re-check
knowledge/prop_firms.json against the new text (snapshots in knowledge/research_out/rules/). Pages that cannot be fetched
are reported, never guessed. Add pages to PAGES (official domains only).
Lucid: its help-center URLs are not public in search results - the owner can add them from inside his account."""
import hashlib, html, json, os, re, sys, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); K = os.path.join(HERE, "knowledge")
STATE = os.path.join(K, "rules_watch.json"); SNAP = os.path.join(K, "research_out", "rules")
PAGES = {
    "Tradeify: essential trading rules": "https://intercom.help/tradeify/en/articles/12268167-essential-trading-rules-overview",
    "FundedNext Futures: automated trading": "https://helpfutures.fundednext.com/en/articles/14298560-is-the-usage-of-automated-trading-systems-eas-and-bots-allowed-in-fundednext-futures",
}


def text_of(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read().decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(Updated|Written by)[^.]{0,60}(ago|this week|today|yesterday)", "", t)     # volatile 'updated x ago' labels
    return t


def main():
    os.makedirs(SNAP, exist_ok=True)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    changed, failed = [], []
    for name, url in PAGES.items():
        try:
            t = text_of(url)
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}"); continue
        h = hashlib.sha1(t.encode()).hexdigest()[:16]; fn = os.path.join(SNAP, re.sub(r"[^A-Za-z0-9]+", "_", name)[:60] + ".txt")
        old = st.get(name, {})
        if old.get("hash") and old["hash"] != h: changed.append(name)
        open(fn, "w").write(t[:200000])
        st[name] = {"url": url, "hash": h, "checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "chars": len(t),
                    "changed_on": datetime.now(timezone.utc).strftime("%Y-%m-%d") if name in changed else old.get("changed_on")}
    json.dump(st, open(STATE, "w"), indent=1)
    print("changed:", changed, "| failed:", failed)
    if changed:
        sys.path.insert(0, HERE)
        import test_engine as TE
        ann = json.load(open(TE.ANN)) if os.path.exists(TE.ANN) else []
        ann.append({"title": "📜 A prop firm changed its official rules", "body": "\n".join(f"- {c}: {PAGES[c]}" for c in changed)
                    + "\nClaude re-checks knowledge/prop_firms.json against the new text."}); json.dump(ann, open(TE.ANN, "w"), indent=1)
        W = json.load(open(os.path.join(K, "wishlist.json"))) if os.path.exists(os.path.join(K, "wishlist.json")) else []
        W.append({"id": (max([w["id"] for w in W]) + 1) if W else 1, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                  "title": "Firm rules changed: re-check prop_firms.json (" + ", ".join(changed)[:80] + ")", "for": "claude", "type": "fix",
                  "why": "The official rule page text changed since last week (snapshots in knowledge/research_out/rules/).",
                  "evidence": "; ".join(PAGES[c] for c in changed)[:300], "impact": "high", "status": "open", "votes": 1})
        json.dump(W, open(os.path.join(K, "wishlist.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
