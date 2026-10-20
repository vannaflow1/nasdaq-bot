"""learn_post.py - posts what the learning session learned to #learning-queue, refreshes the
knowledge digest that /ask uses, and the status fields /learning shows. Runs on push of
knowledge/learned_today.json."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import qqq_gex_daily as q
K = os.path.join(HERE, "knowledge"); TODAY = os.path.join(K, "learned_today.json")
LIB = os.path.join(K, "library.jsonl"); DIGEST = os.path.join(K, "digest.json")
RUNS = os.path.join(HERE, "runs.json"); STATUS = os.path.join(HERE, "status.json")
POSTED = os.path.join(K, "posted.json")
HOOK = os.environ.get("DISCORD_WEBHOOK_LEARN") or os.environ.get("DISCORD_WEBHOOK_BRAIN") or None
STARS = lambda n: "★" * int(n) + "☆" * (5 - int(n))


def post_paper(it):
    idea = it.get("idea") or {}
    parts = [f"**What I learned:** {it['learned']}",
             f"**Key concepts:** {', '.join(it.get('concepts', []))}",
             f"**Trading relevance:** {STARS(it.get('relevance', 0))} - {it.get('relevance_note', '')}"]
    if idea.get("text"):
        parts.append(f"**Idea:** {idea['text']}")
        parts.append(f"**Tested on my memory:** {idea.get('verdict', 'not testable with my data')}"
                     + (f"\n{idea['detail']}" if idea.get("detail") else ""))
    parts.append(f"[{it.get('source', 'paper')}]({it['url']})")
    q.push(it["title"][:200], "\n\n".join(parts), priority="low", tags="bulb", hook=HOOK)


def main():
    lib0 = [json.loads(l) for l in open(LIB) if l.strip()] if os.path.exists(LIB) else []
    posted = set(json.load(open(POSTED))) if os.path.exists(POSTED) else set()
    for it in lib0:                                   # everything learned but not announced yet
        if it["id"] not in posted:
            if it.get("relevance", 0) >= 3 or it.get("curated"):       # only post what is worth reading
                post_paper(it)
            posted.add(it["id"])
    json.dump(sorted(posted), open(POSTED, "w"))
    ann = os.path.join(K, "announce.json")             # one-off notes (corrections etc.)
    if os.path.exists(ann):
        for a in json.load(open(ann)):
            q.push(a["title"][:200], a["body"], priority="default", tags="warning", hook=HOOK)
        os.remove(ann)
    if os.path.exists(TODAY):
        raw = open(TODAY, "rb").read(); h = hashlib.sha1(raw).hexdigest()[:12]
        runs = json.load(open(RUNS)) if os.path.exists(RUNS) else {}
        items = json.loads(raw)
        if runs.get("learn_posted") != h:
            if items.get("reflection"):
                q.push(f"Learning journal - {items.get('date', '')}", items["reflection"], priority="low", tags="books", hook=HOOK)
            runs["learn_posted"] = h
            json.dump(runs, open(RUNS, "w"), indent=1)
    lib = lib0
    dig = [{"title": x["title"], "learned": x["learned"], "concepts": x.get("concepts", []),
            "relevance": x.get("relevance", 0), "verdict": (x.get("idea") or {}).get("verdict"), "url": x["url"],
            "date": x.get("date")} for x in reversed(lib)][:300]
    json.dump(dig, open(DIGEST, "w"), indent=0)
    try:
        st = json.load(open(STATUS))
    except Exception:
        st = {}
    tested = [x for x in lib if (x.get("idea") or {}).get("tested")]
    sk = os.path.join(K, "skipped.jsonl")
    n_skip = sum(1 for l in open(sk) if l.strip()) if os.path.exists(sk) else 0
    lines = [f"LEARNING: {len(lib)} papers read ({n_skip} more skipped as not relevant enough), {len(tested)} ideas tested on my memory, "
             f"{sum(1 for x in tested if 'PROMISING' in (x['idea'].get('verdict') or '').upper())} promising.", ""]
    for x in [d for d in dig if d["relevance"] >= 3][:6]:
        lines.append(f"• {x['title'][:110]} ({STARS(x['relevance'])})")
        lines.append(f"  {x['learned'][:220]}")
        if x.get("verdict"):
            lines.append(f"  tested: {x['verdict'][:160]}")
    try:
        from datetime import datetime, timezone
        d = datetime.now(timezone.utc).isocalendar(); w = json.load(open(os.path.join(K, "engine_stats.json"))).get(f"{d[0]}-W{d[1]:02d}", {})
        if w:
            lines.append(f"This week's tests: {w.get('tested', 0)} run - {w.get('promising', 0)} promising, "
                         f"{w.get('not_confirmed', 0)} not confirmed, {w.get('unfit', 0)} don't fit my data, "
                         f"{w.get('failed', 0)} translation failures")
    except Exception:
        pass
    queue = json.load(open(os.path.join(K, "queue.json"))) if os.path.exists(os.path.join(K, "queue.json")) else []
    lines.append(""); lines.append(f"{len(queue)} papers waiting in my queue.")
    st["learning"] = lines
    json.dump(st, open(STATUS, "w"), indent=1)


if __name__ == "__main__":
    main()
