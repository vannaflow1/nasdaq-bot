"""
learn_fetch.py - finds new research for Volta's learning queue (daily, GitHub Actions).
Sources: arXiv quantitative finance (open access) and OpenAlex open-access works.
Ranks by relevance to what the bot does (options, volatility, dealer hedging, intraday NQ/index
futures, forecasting). Adds the best few to knowledge/queue.json and announces them.
The reading + testing happens in the daily learning session (see knowledge/README.md).
"""
import json, os, re, sys, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
K = os.path.join(HERE, "knowledge"); QUEUE = os.path.join(K, "queue.json"); SEEN = os.path.join(K, "seen.json")
UA = {"User-Agent": "volta-research/1.0"}
CORE = {  # what Volta actually does - a paper must hit at least one of these
    r"\boptions?\b|implied vol|\bvix\b|vxn|variance risk premium|volatility risk premium|\bvrp\b": 3,
    r"\bgamma\b|dealer|market maker|hedging (demand|pressure|flow)": 4,
    r"0dte|zero.day|short.dated|expiration": 4,
    r"realized vol|volatility forecast|\bhar\b|intraday volatility|range": 3,
    r"intraday|overnight|opening|closing auction|end.of.day": 2,
    r"(index|equity|stock) futures|nasdaq|s&p ?500|\bspx\b|\bspy\b|\bqqq\b|\bndx\b": 3,
    r"fomc|cpi|macro(economic)? announcement|scheduled announcement|news release": 3,
}
BROAD = {  # wider trading toolbox: models, risk, strategy research - also welcome
    r"\bgarch\b|\barch\b|egarch|gjr|heterosk|heterosc|stochastic volatility|heston|jump.diffusion|rough volatility|black.scholes|local volatility": 3,
    r"regime.switching|hidden markov|markov.switching|kalman|state.space|change.point": 3,
    r"machine learning|neural network|deep learning|lstm|transformer|reinforcement learning|random forest|gradient boosting": 2,
    r"backtest|overfitting|data.snooping|multiple testing|deflated sharpe|p.hacking|out.of.sample": 3,
    r"kelly|position sizing|risk management|drawdown|value.at.risk|expected shortfall|tail risk|extreme value|stop.loss": 3,
    r"limit order book|order book|microstructure|bid.ask|market making|execution|slippage|transaction cost": 2,
    r"trend.following|time.series momentum|mean reversion|pairs trading|statistical arbitrage|technical (analysis|trading)": 3,
    r"volatility (targeting|timing|clustering)|stylized facts|fat tails|heavy tails|autocorrelation": 2,
    r"monte carlo|bootstrap|copula|portfolio optimization|factor model": 1,
}
EXTRA = {r"skew": 1, r"order flow|price impact|liquidity": 1, r"momentum|reversal": 1, r"regime": 1, r"forecast|predict": 1}
NEG = (r"insurance|credit default|\bcds\b|real estate|housing|agricultur|carbon|esg|climate|blockchain technology|"
       r"sovereign debt|banking|pension|corporate governance|\bipo\b|merger|accounting|venture|household|labor|education|electricity")
OTHER_ASSET = r"crypto|bitcoin|ethereum|\bbond|treasury|exchange rate|currenc|\bfx\b|commodit|oil price"   # allowed, mild penalty


def score(text, title=""):
    t, tt = text.lower(), title.lower()
    core = sum(w for p, w in CORE.items() if re.search(p, t)) + sum(w for p, w in BROAD.items() if re.search(p, t))
    if core == 0:
        return 0
    s = core + sum(w for p, w in EXTRA.items() if re.search(p, t))
    s += 3 if any(re.search(p, tt) for p in list(CORE) + list(BROAD)) else 0   # trading topic right in the title
    s -= 2 if re.search(OTHER_ASSET, tt) else 0
    return s - (8 if re.search(NEG, tt) else 4 if re.search(NEG, t) else 0)


def arxiv(days=3):
    cats = "+OR+".join(f"cat:q-fin.{c}" for c in ("TR", "ST", "PR", "RM", "MF", "CP"))
    u = f"http://export.arxiv.org/api/query?search_query={cats}&sortBy=submittedDate&sortOrder=descending&max_results=80"
    root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        pub = e.find("a:published", ns).text[:10]
        if datetime.fromisoformat(pub).date() < (datetime.now(timezone.utc) - timedelta(days=days)).date():
            continue
        title = " ".join(e.find("a:title", ns).text.split()); ab = " ".join(e.find("a:summary", ns).text.split())
        link = e.find("a:id", ns).text.replace("http://", "https://")
        out.append({"id": "arxiv:" + link.rsplit("/", 1)[-1], "title": title, "abstract": ab, "url": link,
                    "pdf": link.replace("/abs/", "/pdf/"), "source": "arXiv", "date": pub})
    return out


def openalex(days=7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    out = []
    for q in ("option implied volatility", "gamma exposure hedging", "variance risk premium",
              "intraday futures volatility", "equity index options"):
        u = ("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "search": q, "filter": f"is_oa:true,from_publication_date:{since}", "per-page": 15,
            "select": "id,title,abstract_inverted_index,publication_date,open_access,doi"}))
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["results"]
        except Exception:
            continue
        for w in res:
            inv = w.get("abstract_inverted_index") or {}
            words = sorted(((p, k) for k, ps in inv.items() for p in ps))
            ab = " ".join(k for _, k in words)
            if not w.get("title") or len(ab) < 200:
                continue
            out.append({"id": "openalex:" + w["id"].rsplit("/", 1)[-1], "title": w["title"], "abstract": ab,
                        "url": (w.get("open_access") or {}).get("oa_url") or w.get("doi") or w["id"],
                        "source": "OpenAlex", "date": w.get("publication_date")})
    return out


BACKFILL = os.path.join(K, "backfill.json")
TOPICS = ["option implied volatility forecasting", "dealer gamma hedging pressure", "variance risk premium equity index",
          "intraday momentum index futures", "volatility risk premium options returns", "order flow price impact futures",
          "realized volatility forecasting HAR", "0DTE options", "options market makers inventory", "VIX term structure",
          "overnight returns equity index", "macroeconomic announcements stock returns", "volatility skew predictability",
          "stock index futures market microstructure", "machine learning volatility prediction",
          "GARCH volatility forecasting", "stochastic volatility model option pricing", "regime switching stock market",
          "backtest overfitting", "position sizing Kelly criterion", "trend following futures", "mean reversion trading strategy",
          "limit order book dynamics", "tail risk hedging", "jump diffusion asset returns", "deep learning financial time series"]


# second track: research about HOW Volta works - methods it can adopt to improve itself (read, never market-tested)
SELF_TOPICS = ["probability of backtest overfitting", "concept drift adaptation survey", "forecast combination ensembles",
               "hidden technical debt machine learning systems", "statistical versus machine learning forecasting methods",
               "time series cross validation walk forward", "online learning non-stationary time series", "conformal prediction time series",
               "language model agents self-improvement", "automated scientific discovery language models", "multiple hypothesis testing finance",
               "meta-learning time series forecasting", "automated machine learning", "model monitoring drift detection production",
               "probabilistic forecasting calibration evaluation", "algorithmic trading system design",
               # neural networks and brain-inspired learning
               "transformer time series forecasting", "temporal fusion transformer", "N-BEATS neural basis expansion forecasting",
               "recurrent neural network financial forecasting", "continual learning catastrophic forgetting",
               "complementary learning systems hippocampus neocortex", "predictive coding cortex", "thousand brains theory cortical columns",
               "hierarchical temporal memory", "world models reinforcement learning", "memory augmented neural networks",
               "free energy principle active inference", "cognitive architecture", "neuromorphic computing learning",
               "deep reinforcement learning trading", "mixture of experts", "uncertainty estimation deep learning ensembles"]
SELF_KEYS = {r"overfit|data.snooping|multiple (testing|hypothes)|false discover|deflated|selection bias": 4,
             r"concept drift|non.?stationar|online learning|adaptive|regime": 3,
             r"forecast(ing)? (combination|ensemble|evaluation|accuracy)|calibrat|conformal|probabilistic forecast": 3,
             r"cross.validation|walk.forward|out.of.sample|backtest": 3,
             r"machine learning|deep learning|neural|ensemble|boosting|random forest|meta.learning|automl|hyperparameter": 2,
             r"language model|llm|agent|self.improv|reflection|automated (research|discovery)|program search": 3,
             r"technical debt|monitoring|production|pipeline|reproducib": 2,
             r"neural network|transformer|recurrent|lstm|attention|mixture of experts|reinforcement learning|world model": 2,
             r"cortex|cortical|neocortex|hippocamp|predictive coding|free energy|active inference|neuromorphic|cognitive architecture|brain": 3,
             r"continual learning|catastrophic forgetting|lifelong learning|memory.augmented|episodic memory": 3,
             r"uncertainty|ensemble": 2,
             r"time series|forecast": 2, r"trading|financ|market": 1}
SELF_STATE = os.path.join(K, "self_track.json")
# third track (Volta's mission since Oct 2026): everything about prop-firm trading - passing evaluations and collecting
# payouts. Convex payoffs (an eval is an option: lose the fee, win payouts), drawdown-constrained sizing, ruin and
# first-passage probabilities, trader incentive contracts, risk management under trailing limits.
PROP_TOPICS = ["proprietary trading firm traders performance", "funded trader evaluation program", "optimal betting drawdown constraint",
               "Kelly criterion drawdown", "portfolio optimization maximum drawdown constraint", "gambler's ruin probability",
               "first passage time random walk barrier", "convex compensation risk taking fund managers", "option-like incentive contracts traders",
               "tournament behavior mutual fund managers", "risk shifting convex payoff", "day trader profitability",
               "intraday momentum stock index futures", "optimal stopping trading", "position sizing risk of ruin",
               "time-varying volatility position sizing volatility targeting", "trailing stop optimal", "optimal stop loss rules",
               "barrier probability Brownian motion drift", "high water mark incentive fees", "risk management trading limits",
               "expected utility of a lottery-like payoff", "prospect theory trading", "retail traders futures losses",
               "volatility managed portfolios", "opening range breakout futures", "time series momentum futures intraday",
               "risk of ruin capital requirements trading"]
PROP_KEYS = {r"drawdown|ruin|first.passage|barrier|absorbing|survival|stopping time": 4,
             r"kelly|optimal (bet|growth|leverage|position|sizing)|fractional|bet siz": 4,
             r"convex|option.like|incentive|compensation|high.water|tournament|risk.shifting|fee structure": 4,
             r"proprietary trad|prop(rietary)? firm|funded trader|evaluation|day.?trad": 4,
             r"stop.loss|trailing stop|take.profit|profit target": 3,
             r"volatility (target|managed|scaling)|risk management|risk limit|value.at.risk": 3,
             r"intraday|futures|momentum|breakout|opening range": 2, r"trading|financ|market|portfolio": 1}
PROP_STATE = os.path.join(K, "prop_track.json")


def self_score(text, title=""):
    t = (title + " " + text).lower()
    s = sum(w for p, w in SELF_KEYS.items() if re.search(p, t))
    return s - (6 if re.search(NEG, t) else 0)


def self_papers(n=2, track="self"):
    """1-2 well-cited open-access papers per run about methods Volta can use on itself (track "self") or about prop-firm
    trading (track "prop", Volta's mission)."""
    topics, state = (PROP_TOPICS, PROP_STATE) if track == "prop" else (SELF_TOPICS, SELF_STATE)
    st = json.load(open(state)) if os.path.exists(state) else {"topic": 0, "page": {}}
    out = []
    for _ in range(3):
        t = topics[st["topic"] % len(topics)]; pg = st["page"].get(t, 1)
        st["topic"] += 1; st["page"][t] = pg + 1
        u = ("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "search": t, "filter": "is_oa:true,has_abstract:true", "sort": "cited_by_count:desc", "per-page": 8, "page": pg,
            "select": "id,title,abstract_inverted_index,publication_date,open_access,doi"}))
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["results"]
        except Exception:
            continue
        for w in res:
            inv = w.get("abstract_inverted_index") or {}
            ab = " ".join(k for _, k in sorted((p, k) for k, ps in inv.items() for p in ps))
            if w.get("title") and len(ab) >= 200:
                out.append({"id": "openalex:" + w["id"].rsplit("/", 1)[-1], "title": w["title"], "abstract": ab, "track": track,
                            "url": (w.get("open_access") or {}).get("oa_url") or w.get("doi") or w["id"],
                            "source": "OpenAlex (prop mission)" if track == "prop" else "OpenAlex (about itself)", "topic": f"{track}: " + t})
        if len(out) >= 8: break
    json.dump(st, open(state, "w"))
    return out


CURATED = os.path.join(K, "curated.json")


def curated(n=3, seen=()):
    """Hand-picked must-read papers on exactly what Volta does (looked up by title on OpenAlex)."""
    titles = json.load(open(CURATED)) if os.path.exists(CURATED) else []
    done = set(json.load(open(os.path.join(K, "curated_done.json")))) if os.path.exists(os.path.join(K, "curated_done.json")) else set()
    out = []
    for t in [t for t in titles if t not in done][:n]:
        done.add(t)
        u = ("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"title.search:{t.replace(',', ' ')}", "per-page": 15,
            "select": "id,title,abstract_inverted_index,publication_date,open_access,doi,cited_by_count"}))
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["results"]
        except Exception:
            continue
        from difflib import SequenceMatcher
        norm = lambda x: re.sub(r"[^a-z0-9 ]", "", (x or "").lower()).strip()
        sim = lambda w: SequenceMatcher(None, norm(w.get("title")), norm(t)).ratio()
        res = sorted(res, key=lambda w: (-round(sim(w), 2), -(w.get("cited_by_count") or 0)))
        for w in res:
            inv = w.get("abstract_inverted_index") or {}
            ab = " ".join(k for _, k in sorted((p, k) for k, ps in inv.items() for p in ps))
            print(f"  curated '{t[:40]}' -> '{(w.get('title') or '')[:60]}' sim={sim(w):.2f} abstract={len(ab)}")
            if w.get("title") and sim(w) >= 0.85:                       # hand-picked: title match is enough
                if len(ab) < 150:
                    ab = "(No abstract available from the open index - this is a well-known paper; use reliable knowledge of it and say so.)"
                out.append({"id": "openalex:" + w["id"].rsplit("/", 1)[-1], "title": w["title"], "abstract": ab,
                            "url": (w.get("open_access") or {}).get("oa_url") or w.get("doi") or w["id"],
                            "source": "Must-read (curated)", "date": w.get("publication_date"), "curated": True})
                break
    json.dump(sorted(done), open(os.path.join(K, "curated_done.json"), "w"))
    return out


def topic_weights():
    """Feedback loop: topics whose papers the brain rated low get used less, then dropped."""
    stars = {}
    for lib in (os.path.join(K, "library.jsonl"), os.path.join(K, "skipped.jsonl")):
        if not os.path.exists(lib):
            continue
        for l in open(lib):
            if l.strip():
                x = json.loads(l)
                if x.get("topic"):
                    stars.setdefault(x["topic"], []).append(x.get("relevance", 0))
    return {t: (sum(v) / len(v) if len(v) >= 3 else 3.0) for t, v in stars.items()}


def openalex_backfill(n=10):
    """Classic, well-cited open-access research - an endless backlog so the brain never runs dry."""
    st = json.load(open(BACKFILL)) if os.path.exists(BACKFILL) else {"topic": 0, "page": {}}
    out = []
    tw = topic_weights()
    live = [t for t in TOPICS if tw.get(t, 3.0) >= 2.5] or TOPICS      # drop topics averaging < 2.5 stars
    for _ in range(len(live)):
        t = live[st["topic"] % len(live)]; pg = st["page"].get(t, 1)
        st["topic"] += 1; st["page"][t] = pg + 1
        u = ("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "search": t, "filter": "is_oa:true,has_abstract:true", "sort": "cited_by_count:desc", "per-page": 10, "page": pg,
            "select": "id,title,abstract_inverted_index,publication_date,open_access,doi"}))
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["results"]
        except Exception:
            continue
        for w in res:
            inv = w.get("abstract_inverted_index") or {}
            ab = " ".join(k for _, k in sorted((p, k) for k, ps in inv.items() for p in ps))
            if w.get("title") and len(ab) >= 200:
                out.append({"id": "openalex:" + w["id"].rsplit("/", 1)[-1], "title": w["title"], "abstract": ab,
                            "url": (w.get("open_access") or {}).get("oa_url") or w.get("doi") or w["id"],
                            "source": "OpenAlex (classic)", "date": w.get("publication_date"), "topic": t})
        if len(out) >= n * 3:
            break
    json.dump(st, open(BACKFILL, "w"))
    return out


PAPERS = os.path.join(K, "papers")


def _text_from(url, limit=60000):
    """Download a paper (PDF or HTML) and return plain text, so the learning session never browses."""
    import io
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read(15_000_000)
    if raw[:4] == b"%PDF":
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(raw)); out = []
        for pg in r.pages[:40]:
            try:
                out.append(pg.extract_text() or "")
            except Exception:
                pass
            if sum(map(len, out)) > limit:
                break
        txt = "\n".join(out)
    else:
        import html as H
        t = raw.decode("utf-8", "replace")
        t = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", t)
        txt = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", txt)).strip()[:limit]


def attach_texts(queue, max_n=12):
    """Pre-download full text for queued papers into knowledge/papers/<id>.txt."""
    os.makedirs(PAPERS, exist_ok=True); n = 0
    for p in queue:
        if p.get("text_file") or p.get("text_failed") or n >= max_n:
            continue
        fn = re.sub(r"[^A-Za-z0-9._-]", "_", p["id"]) + ".txt"
        for u in [p.get("pdf"), p.get("url")]:
            if not u or not u.startswith("http"):
                continue
            try:
                txt = _text_from(u)
                if len(txt) > 2000:
                    open(os.path.join(PAPERS, fn), "w").write(txt); p["text_file"] = f"knowledge/papers/{fn}"; break
            except Exception:
                continue
        if not p.get("text_file"):
            p["text_failed"] = True                    # session falls back to the abstract
        n += 1


def main(max_new=10):
    os.makedirs(K, exist_ok=True)
    seen = set(json.load(open(SEEN))) if os.path.exists(SEEN) else set()
    queue = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    found, errs = [], []
    queue_len = len(json.load(open(QUEUE))) if os.path.exists(QUEUE) else 0
    try:
        cur = curated(3, seen)
        for p in cur:
            if p["id"] not in seen and not any(q["id"] == p["id"] for q in queue):
                p["score"] = 99; seen.add(p["id"]); p["abstract"] = p["abstract"][:2500]
                p["queued"] = datetime.now(timezone.utc).date().isoformat(); queue.append(p)
    except Exception as e:
        errs.append(f"curated: {type(e).__name__}")
    for fn in (arxiv, openalex) + ((openalex_backfill,) if queue_len < 15 else ()):
        try:
            found += fn()
        except Exception as e:
            errs.append(f"{fn.__name__}: {type(e).__name__}")
    new = []
    for p in found:
        if p["id"] in seen or any(q["id"] == p["id"] for q in queue):
            continue
        p["score"] = score(p["title"] + " " + p["abstract"], p["title"]) if len(p["title"].split()) >= 3 else 0
        seen.add(p["id"])
        if p["score"] >= 6:
            new.append(p)
    new = sorted(new, key=lambda p: -p["score"])[:max_new]
    try:                                                     # self track: keep ~2 papers about Volta's own methods waiting
        waiting = sum(1 for q in queue if q.get("track") == "self")
        if waiting < 2:
            cand = []
            for p in self_papers():
                if p["id"] in seen or any(q["id"] == p["id"] for q in queue): continue
                p["score"] = self_score(p["abstract"], p["title"]); seen.add(p["id"])
                if p["score"] >= 3: cand.append(p)              # topic search already targets; the reader judges usefulness
            new += sorted(cand, key=lambda p: -p["score"])[:2 - waiting]
    except Exception as e:
        errs.append(f"self: {type(e).__name__}")
    try:                                                     # prop track (the mission): keep ~3 papers waiting, read first
        waiting = sum(1 for q in queue if q.get("track") == "prop")
        if waiting < 3:
            cand = []
            for p in self_papers(track="prop"):
                if p["id"] in seen or any(q["id"] == p["id"] for q in queue): continue
                t = (p["title"] + " " + p["abstract"]).lower()
                p["score"] = sum(w for k, w in PROP_KEYS.items() if re.search(k, t)) - (6 if re.search(NEG, t) else 0); seen.add(p["id"])
                if p["score"] >= 4: cand.append(p)
            new += sorted(cand, key=lambda p: -p["score"])[:3 - waiting]
    except Exception as e:
        errs.append(f"prop: {type(e).__name__}")
    for p in new:
        p["abstract"] = p["abstract"][:2500]; p["queued"] = datetime.now(timezone.utc).date().isoformat()
    queue += new
    try:
        attach_texts(queue)
    except Exception as e:
        errs.append(f"texts: {type(e).__name__}")
    json.dump(queue, open(QUEUE, "w"), indent=1)
    json.dump(sorted(seen)[-5000:], open(SEEN, "w"))
    print(f"scanned {len(found)} papers, queued {len(new)}, queue size {len(queue)}", errs)
    if new:
        import qqq_gex_daily as q
        body = "\n".join(f"• **{p['title'][:150]}** ({p['source']}, relevance {p['score']})" for p in new)
        q.push(f"Learning queue: +{len(new)} paper{'s' if len(new) > 1 else ''}",
               body + f"\n\n{len(queue)} waiting. I read them in tonight's learning session.",
               priority="low", tags="books", hook=os.environ.get("DISCORD_WEBHOOK_LEARN") or os.environ.get("DISCORD_WEBHOOK_BRAIN") or None)


if __name__ == "__main__":
    main()
