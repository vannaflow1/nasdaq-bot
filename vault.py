"""vault.py - builds Volta's knowledge as an Obsidian vault (knowledge/vault/), regenerated after every learning run.
Open the folder in Obsidian (free) -> Graph view: papers, concepts, ideas, verdicts and the parts of Volta they touch,
all linked. Nothing in here is hand-edited; it is rebuilt from knowledge/library.jsonl and the test logs."""
import json, os, re, shutil
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); V = os.path.join(K, "vault")

SYSTEM = {
    "Volta": ("hub", "Volta - the whole system. Start here.",
              ["Brain", "Neural net (live)", "Live tracker", "Options nerd", "Short-vol strategy", "Research engine",
               "Near-miss pool", "Open read (powers)", "Questions Volta asked", "Strategy lab", "Self-check", "Market data"]),
    "Brain": ("system", "Forecasts tomorrow's NQ high-to-low range every evening (ridge model on options + volatility readings, "
              "12 years of memory). Walk-forward 2017-2025: avg miss 0.53% vs 0.55% for the options market alone; 80% band held 80%. "
              "Grades itself every day; retrains monthly and only promotes a new version if it wins on unseen days.",
              ["Market data", "Gamma regime", "Neural net (live)"]),
    "Neural net (live)": ("system", "5 small neural networks (64-32 neurons) trained on 1-minute NQ 2014-2025, blended with the linear "
                          "in-session model. Re-estimates the day's range during the session: 3% more accurate, better in 7/7 unseen years. "
                          "On the daily brain a neural net LOST in 9/9 years - too little data - so it is not used there.",
                          ["Live tracker", "Brain"]),
    "Live tracker": ("system", "#live: every 5 minutes in the US session. 16:00 update, range-used alerts, far-level alerts.",
                     ["Neural net (live)"]),
    "Options nerd": ("system", "#options and /nerd: dealer gamma/vanna/charm, skew, term structure, implied moves. Context only - "
                     "tested as forecast inputs, no added accuracy; no direction edge (147 tests, see Directional Greeks).",
                     ["Gamma regime", "Directional Greeks"]),
    "Short-vol strategy": ("system", "The one options edge found: sell the nearest QQQ straddle / 2x iron fly on HIGH-gamma days "
                           "(rank > 0.7). Real prices 2017-2025: straddle +14.3 bp/trade t 5.3, iron fly +8.1 bp t 3.3, 8/9 years "
                           "positive, placebo p < 0.001. Paper-traded live by /shortvol.", ["Gamma regime"]),
    "Research engine": ("system", "Reads papers around the clock (free AI), turns testable ideas into formulas and tests them on "
                        "Volta's memory: range ideas vs the brain, direction ideas vs holding the same exposure, options ideas as real "
                        "QQQ option trades with spreads and a placebo.",
                        ["PROMISING", "NOT CONFIRMED", "DOESN'T FIT", "TRANSLATION FAILED", "Near-miss pool"]),
    "Near-miss pool": ("system", "Ideas that helped the range forecast a little and fairly consistently. Re-tested TOGETHER every month: "
                       "best mix picked on older years, judged on the last 3 unseen years.", ["Brain"]),
    "Open read (powers)": ("system", "New powers (20 Oct 2026), posted at the NY open in #live and /powers: odds that yesterday's high "
                           "/ low get taken (AUC 0.80 / 0.78), that the gap fills (0.71), tail-day risk (0.78) - all calibrated on unseen "
                           "years 2017-2025. Asia/London sweep base rates. NOT predictable: trend vs chop day, first-hour continuation.",
                           ["Brain", "Research engine"]),
    "Questions Volta asked": ("system", "Volta's own questions about the NY session, asked from what it read (curiosity) or while testing "
                              "papers. Every question gets the plain fact first, then a walk-forward test of whether anything known at "
                              "the open predicts it. A leak guard stops the answer side from being used as a predictor.",
                              ["Research engine", "Open read (powers)"]),
    "Strategy lab": ("system", "Complete intraday NQ strategies (entry, filter, stop, target, time exit) as JSON specs, backtested on "
                     "1-minute NQ 2014-2023 with pessimistic fills and costs; must beat random entries, survive a stress test and pass a "
                     "locked 2024-2026 exam (max 10 exams/week). Passing strategies are forward-tested every evening. Volta designs "
                     "strategies itself (every second curiosity turn). 20 Oct 2026: mechanical fades of yesterday's high/low, Asia/London, "
                     "VWAP bands and the midnight open all lose (stops run ~70%), with or without confluence.",
                     ["Research engine", "Open read (powers)", "Questions Volta asked"]),
    "Self-check": ("system", "Once a day Volta reviews its own state (scores, failures and their reasons, near-misses), writes a "
                   "diary, queues follow-up questions/strategies it can run itself, and files wishes for what it can't do alone - for "
                   "Claude (research-side code/data, granted in the Sunday session) or for the owner (his data, money, accounts, live decisions).",
                   ["Research engine", "Strategy lab", "Questions Volta asked"]),
    "Market data": ("system", "NQ 1-minute 2014-2026, QQQ option chains 2011-2025 (15M rows: surface, skew, open interest, Heston fits), "
                    "live CBOE delayed chains, Yahoo prices. Market-wide (Oct 2026): VIX, VIX9D, VIX3M, VVIX, VIX1D, ES/S&P 500, "
                    "10-year yield, dollar - daily since 2010. SPX options summarised every evening from 19 Oct 2026 (history builds up).", []),
    "Gamma regime": ("finding", "PROVEN: low dealer gamma -> bigger next-day moves; high gamma -> calmer days and overpriced options. "
                     "Size signal only - never direction.", ["Brain", "Short-vol strategy"]),
    "Directional Greeks": ("finding", "Tested 19 Oct 2026: 21 options readings x 7 horizons, plus dealer-flow theories (gamma momentum, "
                           "vanna after IV spikes, charm into opex). None beat the placebo. Found and removed a 16:15 timing leak.", []),
    "PROMISING": ("verdict", "Beat the baseline on unseen data - goes to the weekly stress test.", []),
    "NOT CONFIRMED": ("verdict", "Tested fairly; did not beat the baseline on unseen data.", []),
    "DOESN'T FIT": ("verdict", "Needs data Volta does not have (order books, sentiment, other assets...).", []),
    "TRANSLATION FAILED": ("verdict", "The free AI could not turn the idea into a valid formula; retried after fixes.", []),
}
SYN = {"implied volatility": "implied volatility", "iv": "implied volatility", "realised volatility": "realized volatility",
       "rv": "realized volatility", "vrp": "volatility risk premium", "variance risk premium": "volatility risk premium",
       "0dte": "0DTE options", "0dte options": "0DTE options", "zero-days-to-expiry options": "0DTE options",
       "har": "HAR model", "har model": "HAR model", "har-rv": "HAR model", "garch": "GARCH", "garch model": "GARCH",
       "machine learning": "machine learning", "neural networks": "neural networks", "neural network": "neural networks",
       "gamma exposure": "dealer gamma", "gex": "dealer gamma", "dealer gamma exposure": "dealer gamma",
       "stochastic volatility": "stochastic volatility", "heston model": "Heston model", "vix": "VIX",
       "har-rv model": "HAR model", "har-rv": "HAR model", "arch": "GARCH", "garch models": "GARCH", "egarch": "GARCH",
       "gjr-garch": "GARCH", "gamma exposure (gex)": "dealer gamma", "dealer gamma": "dealer gamma", "gamma risk": "dealer gamma",
       "deep neural networks": "neural networks", "deep learning": "neural networks", "lstm": "neural networks",
       "fomc": "FOMC", "fomc announcements": "FOMC", "realized variance": "realized volatility"}
CONCEPT_SYS = [("volatil|garch|har model|range|variance", "Brain"), ("gamma|dealer|hedg", "Gamma regime"),
               ("0dte|option|straddle|premium|skew|smile", "Short-vol strategy"), ("neural|machine learning|deep", "Neural net (live)"),
               ("direction|momentum|return predict", "Directional Greeks")]


def slug(t):
    return re.sub(r"[\\/:*?\"<>|#^\[\]]", "", t).strip()[:90]


def norm(c):
    c = re.sub(r"\s*\(.*?\)", "", c)
    k = c.strip().lower().rstrip("s") if len(c) > 4 else c.strip().lower()
    k2 = c.strip().lower()
    return SYN.get(k2) or SYN.get(k) or c.strip().lower()


def verdict_link(v):
    v = str(v or "")
    for k in ("PROMISING", "NOT CONFIRMED", "DOESN'T FIT", "TRANSLATION FAILED"):
        if v.startswith(k): return k
    return None


def build():
    lib = [json.loads(l) for l in open(os.path.join(K, "library.jsonl")) if l.strip()]
    pool = json.load(open(os.path.join(K, "feature_pool.json"))) if os.path.exists(os.path.join(K, "feature_pool.json")) else []
    pool_ids = {p.get("id") for p in pool}
    if os.path.exists(V): shutil.rmtree(V)
    for d in ("Papers", "Concepts", "System", "Questions"): os.makedirs(os.path.join(V, d))
    qf = os.path.join(K, "questions.jsonl")
    qs = [json.loads(l) for l in open(qf) if l.strip()] if os.path.exists(qf) else []
    for i, q in enumerate(qs):
        vl = verdict_link(q.get("verdict")) or ("FACT" if str(q.get("verdict", "")).startswith("FACT") else None)
        own = q.get("source") == "curiosity"
        lines = ["---", f"tags: [question{', curiosity' if own else ''}]", f"asked: {q.get('date')}", "---", f"# {q.get('question')}",
                 ("Volta asked this itself." if own else "Asked while testing a paper.") + f" Inspired by: {q.get('inspired_by', '')}", "",
                 f"Answer formula: `{q.get('target')}`", f"Predictor: `{q.get('expr') or '(none - a pure fact)'}`", "",
                 (f"[[{vl}]] - " if vl and vl != "FACT" else "") + str(q.get("verdict")), "", "Part of [[Questions Volta asked]]"]
        open(os.path.join(V, "Questions", f"Q{i + 1:03d} " + slug(str(q.get("question")))[:70] + ".md"), "w").write("\n".join(lines))
    cpapers = defaultdict(list)
    for x in lib:
        for c in x.get("concepts") or []:
            cpapers[norm(c)].append(x["title"])
    shared = {c for c, ps in cpapers.items() if len(ps) >= 2}            # concept notes only where they connect papers
    for x in lib:
        i = x.get("idea") or {}; vl = verdict_link(i.get("verdict"))
        kind = (i.get("spec") or {}).get("kind")
        part = {"range": "Brain", "template": "Brain", "direction": "Options nerd", "options": "Short-vol strategy", "power": "Open read (powers)"}.get(kind)
        cons = []
        for c in x.get("concepts") or []:
            n = norm(c); cons.append(f"[[{slug(n)}]]" if n in shared else n)
        stars = "★" * int(x.get("relevance") or 0) + "☆" * (5 - int(x.get("relevance") or 0))
        body = [f"---", f"tags: [paper{', curated' if x.get('curated') else ''}]", f"relevance: {x.get('relevance')}",
                f"read: {x.get('date')}", "---", f"# {x['title']}", f"{stars}  ·  {x.get('source', '')}  ·  [source]({x.get('url', '')})", "",
                "## What Volta learned", x.get("learned") or "", "", "## Why it matters (or not)", x.get("relevance_note") or "", "",
                "## Concepts", ", ".join(cons) or "-", ""]
        if x.get("track") == "self":
            body += ["## Lesson for Volta", x.get("lesson") or "-", "", "Feeds [[Self-check]]"]
        if i.get("text"):
            body += ["## Idea", i["text"], "", "## Test", (f"[[{vl}]] - " if vl else "") + str(i.get("verdict") or "not tested yet")]
            if i.get("detail"): body.append(f"How: {i['detail']}")
            if part: body.append(f"Touches: [[{part}]]")
            if x["id"] in pool_ids: body.append("In the [[Near-miss pool]] - re-tested together with the others monthly.")
        body += ["", "Part of [[Research engine]]" if x.get("track") != "self" else "Read about itself - part of [[Self-check]]"]
        open(os.path.join(V, "Papers", slug(x["title"]) + ".md"), "w").write("\n".join(body))
    for c in shared:
        lines = [f"---", "tags: [concept]", "---", f"# {c}", f"{len(cpapers[c])} papers mention this:", ""]
        lines += [f"- [[{slug(t)}]]" for t in sorted(set(cpapers[c]))]
        rel = [sysn for pat, sysn in CONCEPT_SYS if re.search(pat, c.lower())]
        if rel: lines += ["", "Related part of Volta: " + ", ".join(f"[[{r}]]" for r in dict.fromkeys(rel))]
        open(os.path.join(V, "Concepts", slug(c) + ".md"), "w").write("\n".join(lines))
    for name, (tag, text, links) in SYSTEM.items():
        lines = ["---", f"tags: [{tag}]", "---", f"# {name}", text, ""] + [f"- [[{l}]]" for l in links]
        if name == "Near-miss pool" and pool:
            lines += ["", "## Members"] + [f"- {p.get('template') or p.get('expr')} ({p['gain']:+.1f}%, {p['years']} years) - {p['paper']}" for p in pool]
            r = os.path.join(K, "pool_review.json")
            if os.path.exists(r):
                rv = json.load(open(r)); lines += ["", f"Last combined test ({rv['date']}): {rv['verdict']} "
                                                   f"(picked {rv.get('gain_pick', 0):+.2f}%, unseen years {rv.get('avg_test', 0):+.2f}%)"]
        if name == "Self-check":
            wf, df = os.path.join(K, "wishlist.json"), os.path.join(K, "diary.jsonl")
            if os.path.exists(df):
                lines += ["", "## Diary"] + [f"- {json.loads(l)['date']}: {json.loads(l)['diary']}" for l in open(df).read().splitlines()[-10:] if l.strip()]
            if os.path.exists(wf):
                lines += ["", "## Wishes"] + [f"- #{w['id']} [{w['status']}, for {w['for']}] {w['title']} - {w['why'][:200]}" for w in json.load(open(wf))]
        if name == "Volta":
            nv = defaultdict(int)
            for x in lib: nv[verdict_link((x.get("idea") or {}).get("verdict")) or "untested"] += 1
            lines += ["", f"Papers read: {len(lib)} · concepts linking 2+ papers: {len(shared)}",
                      "Verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(nv.items()))]
        open(os.path.join(V, "System", slug(name) + ".md"), "w").write("\n".join(lines))
    os.makedirs(os.path.join(V, ".obsidian"))
    groups = [("path:Questions", 0xD6336C), ("path:System", 0x7048E8), ("tag:#finding", 0x2F9E44), ("tag:#verdict", 0xF08C00), ("path:Concepts", 0x1C7ED6),
              ("tag:#curated", 0xE03131), ("path:Papers", 0x868E96)]
    json.dump({"colorGroups": [{"query": q, "color": {"a": 1, "rgb": c}} for q, c in groups], "showTags": False,
               "showOrphans": True, "nodeSizeMultiplier": 1.2, "lineSizeMultiplier": 0.6, "repelStrength": 12,
               "linkDistance": 160}, open(os.path.join(V, ".obsidian", "graph.json"), "w"), indent=1)
    print(f"vault: {len(lib)} papers, {len(shared)} concepts, {len(SYSTEM)} system notes")


if __name__ == "__main__":
    build()
