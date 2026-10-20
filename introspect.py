"""introspect.py - Volta's daily self-check. Volta reads a digest of its OWN state (scores, failures and why, near-misses,
open wishes), writes a short diary, queues follow-up questions/strategies it can run itself, and files WISHES for what it
can't do alone: for Claude (code/data work on the research side) or for the owner (data he owns, money, accounts, decisions).
Runs once a day inside the learning run, on the free AI. It never changes code itself."""
import difflib, json, os, re, sys
from collections import Counter
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
STATE, WISH, DIARY = (os.path.join(K, f) for f in ("introspect_state.json", "wishlist.json", "diary.jsonl"))


def _jl(path):
    return [json.loads(l) for l in open(path) if l.strip()] if os.path.exists(path) else []


def digest():
    import pandas as pd
    out = []
    try:
        import vault
        out.append("MY PARTS: " + "; ".join(f"{k}: {v[1][:110]}" for k, v in vault.SYSTEM.items() if v[0] in ("system", "finding")))
    except Exception:
        pass
    try:
        p = pd.read_csv(os.path.join(HERE, "brain_preds.csv")).dropna(subset=["actual"])
        if len(p):
            miss = (abs(p.actual - p.pred) / p.actual).mean(); inb = ((p.actual >= p.lo) & (p.actual <= p.hi)).mean()
            out.append(f"MY LIVE RANGE FORECASTS: {len(p)} graded, avg miss {miss:.0%} of the actual range, inside my 80% band {inb:.0%}")
        else:
            out.append("MY LIVE RANGE FORECASTS: none graded yet")
    except Exception:
        pass
    st = json.load(open(os.path.join(K, "engine_stats.json"))) if os.path.exists(os.path.join(K, "engine_stats.json")) else {}
    if st: out.append("IDEA TESTS BY WEEK: " + "; ".join(f"{w}: {json.dumps(v)}" for w, v in list(st.items())[-2:]))
    lib = _jl(os.path.join(K, "library.jsonl"))
    reasons = Counter()
    for x in lib:
        v = str((x.get("idea") or {}).get("verdict") or "")
        if v.startswith("DOESN'T FIT") or v.startswith("TRANSLATION FAILED"):
            m = re.search(r"(needs?|requires?|unknown column|unknown template|not allowed)[^.;|]{0,70}", v, re.I)
            reasons[(m[0] if m else v[:70]).lower().strip()] += 1
    if reasons: out.append("WHY IDEAS FAILED ME (count): " + "; ".join(f"{n}x {r}" for r, n in reasons.most_common(8)))
    pool = json.load(open(os.path.join(K, "feature_pool.json"))) if os.path.exists(os.path.join(K, "feature_pool.json")) else []
    if pool: out.append("NEAR-MISS FEATURES: " + "; ".join(f"{p.get('template') or p.get('expr')} ({p['gain']:+.1f}%, {p['years']})" for p in pool[-6:]))
    S = _jl(os.path.join(K, "strategies.jsonl"))
    if S:
        top = sorted([e for e in S if (e.get("insample") or {}).get("n", 0) >= 80], key=lambda e: -e["insample"].get("avg_R", -9))[:4]
        out.append(f"STRATEGIES: {len(S)} tested, {sum(str(e.get('verdict', '')).startswith('PROMISING STRATEGY') for e in S)} passed. Best in-sample: "
                   + "; ".join(f"{e['name'][:60]} ({e['insample']['n']} trades, {e['insample']['avg_R']:+.2f}R, {e['insample']['years_pos']} yrs)" for e in top))
    Q = _jl(os.path.join(K, "questions.jsonl"))
    if Q: out.append(f"QUESTIONS I ASKED: {len(Q)}. Latest: " + " | ".join(f"{q['question'][:70]} -> {str(q['verdict'])[:60]}" for q in Q[-5:]))
    W = json.load(open(WISH)) if os.path.exists(WISH) else []
    if W: out.append("MY WISHES ALREADY FILED: " + "; ".join(f"#{w['id']} [{w['status']}] {w['title'][:70]}" for w in W[-12:]))
    rec = [x for x in sorted(lib, key=lambda x: x.get("date", ""))[-12:] if (x.get("relevance") or 0) >= 4]
    if rec: out.append("RECENT GOOD PAPERS: " + "; ".join(x["title"][:80] for x in rec[-5:]))
    me = [x for x in lib if x.get("track") == "self" and x.get("lesson")][-6:]
    if me: out.append("WHAT I READ ABOUT IMPROVING MYSELF (paper -> lesson): " + " || ".join(f"{x['title'][:70]} -> {x['lesson'][:200]}" for x in me))
    try:
        import volta_book
        a = volta_book.load(); J = _jl(volta_book.JOURNAL)[-5:]
        out.append(f"MY TRADING BOOK (virtual 25K prop account #{a['account']}, blown so far {a['blown']}): balance ${a['balance']:,.0f}, "
                   f"{a['trades']} trades. Last journal: " + " | ".join(str(j.get('result') or j.get('decision'))[:80] for j in J))
    except Exception:
        pass
    D = _jl(DIARY)
    if D: out.append("MY LAST DIARY ENTRIES: " + " || ".join(d["diary"][:200] for d in D[-3:]))
    return "\n".join(out)


SYSTEM = """You are Volta, a self-improving research bot for Nasdaq futures (NQ) and QQQ options. YOUR ONE MISSION (since Oct 2026):
become an automated trader that passes Lucid prop evaluations and keeps generating payouts (objective: expected payouts
per evaluation minus its fee, measured in your prop simulator under Lucid's exact rules). Judge everything by that. Every day you reflect on
YOUR OWN state (below) like a scientist reviewing their lab: what works, what keeps failing and why, what you are missing.
Then you decide how to improve yourself. You can do three things:
1. diary: 3-5 honest sentences about what you learned about yourself and what you will try next.
2. self_actions (max 2): follow-ups you can run yourself RIGHT NOW with your existing tools - a new question or strategy
   that digs into a near-miss or a pattern in your failures. Each is {"why": "...", "spec": <a question or strategy spec>}.
   Question spec: {"kind":"question","question":"...","target":"<y_ formula>","expr":"<known-columns formula or empty>"}
   Strategy spec: {"kind":"strategy","name":"...","entry":{...},"filter":"...","stop":{...},"target":{...},"exit":"14:55"}
   Use only columns/levels that exist (k_*, p_*, y_* for targets only, pw_*, gex_rank, iv30, vix, vix_curve, nq_vs_es,
   levels yday_high/low, asia_high/low, london_high/low, on_high/low, or15_high/low, vwap bands, open, midnight_open).
3. wishes (max 2, only if genuinely useful and NOT already filed): something you cannot do alone.
   {"title": "<short>", "for": "claude|owner", "type": "data|code|fix|decision", "why": "...", "evidence": "<numbers from
   your state>", "impact": "high|medium|low"}
   "claude" = any code or free-data work, including improvements to your live briefings/alerts/forecasts - Claude only
   ships them if they are verifiably better (beats the current version on unseen data / passes all dry runs).
   "owner" = ONLY things only he can provide: data he owns (e.g. his ES/SPX history, his trade log), anything that costs
   money, or anything needing his accounts.
Self-actions must be about MARKETS (what NQ does in a session), never about your own software - software problems go
into a wish for Claude. What you ALREADY HAVE (never wish for these): dealer gamma/vanna/charm ESTIMATES from QQQ, NDX and
(since Oct 2026) SPX option chains, 12 years of daily QQQ option history with the vol surface and Heston fits, 1-minute NQ
2014-2026, 1-minute ES 2014-2026 (NQ/ES SMT divergence), NYSE TICK breadth 2014-2026, SPX weekly options tick data 2019-2025 (real dealer gamma from OI and from customer buy/sell flow, walls, 0DTE positioning), VIX family, ES/S&P, rates, dollar, the live CBOE delayed QQQ chain every 30 minutes during the session.
True dealer POSITIONS (who is long/short) are not sold to retail; do not wish for them.
When a lesson from the research about yourself fits a weakness in your numbers, turn it into a wish for Claude (say which
paper it comes from). Be specific and grounded in the numbers. Never wish for something you already have. Reply ONLY with one JSON object:
{"diary": "...", "self_actions": [...], "wishes": [...]}"""


def run(ask):
    today = datetime.now(timezone.utc).date().isoformat()
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if st.get("date") == today: return 0.0
    import test_engine as T
    out, units = ask(SYSTEM, digest())
    try:
        r = T.first_json(out)
    except Exception as e:
        print("self-check: unusable reply", e); return units
    st["date"] = today; json.dump(st, open(STATE, "w"))
    diary = str(r.get("diary", "")).strip()[:900]
    # 1. self-actions -> straight into the test queue (the engine validates and guards them like any idea)
    tq = json.load(open(T.TESTQ)) if os.path.exists(T.TESTQ) else []
    queued = []
    for j, a in enumerate((r.get("self_actions") or [])[:2]):
        spec = a.get("spec") if isinstance(a, dict) else None
        if not isinstance(spec, dict) or spec.get("kind") not in ("question", "strategy"): continue
        spec["_source"] = "self-check"
        txt = spec.get("question") or ("Strategy: " + str(spec.get("name", "")))
        tq.append({"id": f"self:{today}:{j}", "title": "Volta's self-check: " + str(a.get("why", ""))[:140], "idea": txt,
                   "relevance": 7, "spec": spec, "source": "curiosity"})
        queued.append(txt[:120])
    json.dump(tq, open(T.TESTQ, "w"), indent=1)
    # 2. wishes -> wishlist (merged with similar open wishes instead of duplicated)
    W = json.load(open(WISH)) if os.path.exists(WISH) else []
    new = []
    for w in (r.get("wishes") or [])[:2]:
        if not isinstance(w, dict) or not w.get("title"): continue
        t = str(w["title"])[:120]
        same = [x for x in W if x["status"] in ("open", "approved") and difflib.SequenceMatcher(None, x["title"].lower(), t.lower()).ratio() > 0.72]
        if same:
            same[0]["votes"] = same[0].get("votes", 1) + 1; same[0]["evidence"] = str(w.get("evidence", same[0].get("evidence", "")))[:300]; continue
        item = {"id": (max([x["id"] for x in W]) + 1) if W else 1, "date": today, "title": t,
                "for": "owner" if str(w.get("for", "")).lower().startswith(("o", "y")) else "claude",
                "type": str(w.get("type", "other"))[:12], "why": str(w.get("why", ""))[:400], "evidence": str(w.get("evidence", ""))[:300],
                "impact": str(w.get("impact", "medium"))[:8], "status": "open", "votes": 1}
        W.append(item); new.append(item)
    json.dump(W, open(WISH, "w"), indent=1)
    with open(DIARY, "a") as f: f.write(json.dumps({"date": today, "diary": diary, "queued": queued, "new_wishes": [w["id"] for w in new]}) + "\n")
    body = [diary]
    if queued: body += ["", "I queued for myself:"] + [f"- {q}" for q in queued]
    if new:
        body += ["", "I need help with:"] + [f"- #{w['id']} {w['title']} ({'needs the owner OK' if w['for'] == 'owner' else 'for Claude on Sunday'}): {w['why'][:200]}" for w in new]
    ann = json.load(open(T.ANN)) if os.path.exists(T.ANN) else []
    ann.append({"title": "🪞 Volta's self-check", "body": "\n".join(body)[:1800]}); json.dump(ann, open(T.ANN, "w"), indent=1)
    write_status(W, diary)
    print("self-check:", diary[:200], "| queued", len(queued), "| new wishes", len(new))
    return units


def write_status(W=None, diary=None):
    W = W if W is not None else (json.load(open(WISH)) if os.path.exists(WISH) else [])
    D = _jl(DIARY); diary = diary or (D[-1]["diary"] if D else "")
    lines = ["VOLTA'S SELF-CHECK" + (f" ({D[-1]['date']})" if D else ""), diary or "No self-check yet.", ""]
    op = [w for w in W if w["status"] in ("open", "approved")]
    if op:
        lines.append("WISHES (what I need to get better):")
        for w in sorted(op, key=lambda w: (w["for"] != "owner", -w.get("votes", 1)))[:10]:
            who = "needs the owner" if w["for"] == "owner" else "for Claude"
            lines.append(f"#{w['id']} [{who}{', approved' if w['status'] == 'approved' else ''}] {w['title']} - {w['why'][:140]}")
    done = [w for w in W if w["status"] == "done"][-3:]
    if done: lines += ["", "Recently granted: " + "; ".join(f"#{w['id']} {w['title'][:60]}" for w in done)]
    import json as _j
    sp = os.path.join(HERE, "status.json")
    s = _j.load(open(sp)) if os.path.exists(sp) else {}
    s["wishes"] = lines; _j.dump(s, open(sp, "w"), indent=1)


if __name__ == "__main__":
    print(digest())
