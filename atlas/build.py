"""atlas/build.py - rebuilds the Volta Atlas page (atlas/volta-atlas.html) from the current knowledge base.
Run by the weekly review, which then republishes it to the same link."""
import json, os, re, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import vault as V
K = os.path.join(HERE, "knowledge")


def build():
    lib = [json.loads(l) for l in open(os.path.join(K, "library.jsonl")) if l.strip()]
    qf = os.path.join(K, "questions.jsonl"); qs = [json.loads(l) for l in open(qf) if l.strip()] if os.path.exists(qf) else []
    cp = defaultdict(list)
    for x in lib:
        for c in x.get("concepts") or []: cp[V.norm(c)].append(x["id"])
    shared = {c for c, ps in cp.items() if len(ps) >= 2}
    nodes, links = [], []
    for name, (tag, text, ls) in V.SYSTEM.items():
        nodes.append({"id": name, "t": "verdict" if tag == "verdict" else ("finding" if tag == "finding" else "system"), "label": name, "text": text})
        links += [[name, l] for l in ls]
    for c in shared:
        nodes.append({"id": "c:" + c, "t": "concept", "label": c, "n": len(set(cp[c]))})
        for pat, s in V.CONCEPT_SYS:
            if re.search(pat, c.lower()): links.append(["c:" + c, s]); break
    for x in lib:
        i = x.get("idea") or {}; vl = V.verdict_link(i.get("verdict"))
        nodes.append({"id": x["id"], "t": "paper", "label": x["title"][:110], "rel": x.get("relevance") or 0, "cur": bool(x.get("curated")),
                      "learned": (x.get("learned") or "")[:420], "idea": (i.get("text") or "")[:260], "verdict": str(i.get("verdict") or "not tested")[:260],
                      "url": x.get("url") or ""})
        links += [[x["id"], "c:" + V.norm(c)] for c in x.get("concepts") or [] if V.norm(c) in shared]
        if vl: links.append([x["id"], vl])
    for k, q in enumerate(qs):
        qid = f"q{k}"; vl = V.verdict_link(q.get("verdict"))
        nodes.append({"id": qid, "t": "question", "label": str(q.get("question"))[:110], "text": str(q.get("verdict"))[:420]})
        links.append([qid, "Questions Volta asked"])
        if vl: links.append([qid, vl])
    ids = {n["id"] for n in nodes}; links = [l for l in links if l[0] in ids and l[1] in ids]
    nn = json.load(open(os.path.join(HERE, "models", "intraday_nn.json"))); net = nn["nets"][0]
    pool = json.load(open(os.path.join(K, "feature_pool.json"))) if os.path.exists(os.path.join(K, "feature_pool.json")) else []
    verd = defaultdict(int)
    for x in lib: verd[V.verdict_link((x.get("idea") or {}).get("verdict")) or "untested"] += 1
    for q in qs: verd[V.verdict_link(q.get("verdict")) or "untested"] += 1
    data = {"nodes": nodes, "links": links,
            "nn": {"features": nn["features"], "W1": [[round(v, 2) for v in r] for r in net["W"][0]], "W2": [[round(v, 2) for v in r] for r in net["W"][1]],
                   "W3": [round(r[0], 2) for r in net["W"][2]], "b1": [round(v, 3) for v in net["b"][0]], "b2": [round(v, 3) for v in net["b"][1]],
                   "b3": round(net["b"][2][0], 3)},
            "stats": {"papers": len(lib), "concepts": len(shared), "verdicts": verd, "pool": len(pool), "questions": len(qs)}}
    smp = json.load(open(os.path.join(HERE, "atlas", "nn_sample.json")))
    t = open(os.path.join(HERE, "atlas", "template.html")).read()
    t = t.replace("__SAMPLE__", json.dumps(smp)).replace("__SAMPLE_TEXT__",
          f"Real sample: 10 Dec 2025, 10:00 Chicago. The brain expected a {smp['pred']}% day; NQ had already moved {smp['so']}%.")
    t = t.replace("__DATA__", json.dumps(data))
    out = os.path.join(HERE, "atlas", "volta-atlas.html"); open(out, "w").write(t)
    print(f"atlas: {len(nodes)} nodes, {len(links)} links, {len(qs)} questions -> {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    build()
