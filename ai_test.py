"""ai_test.py - compares the free Cloudflare models on Volta's real jobs (triage + paper reading + JSON discipline).
Prints quality signals and cost only; never prints the worker address."""
import json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import learn_read as L
import test_engine as T
PAPER = ("Title: Gamma exposure and intraday volatility in index options\nAbstract: We show that when market makers hold "
         "net negative gamma in S&P 500 index options, intraday realized volatility of index futures is 30-40% higher and "
         "intraday momentum stronger, while positive dealer gamma predicts mean reversion of the open-to-close return.")
SYS = ("You are Volta's research reader. Reply ONLY with JSON: {\"learned\": \"<2-3 sentences>\", \"concepts\": [\"3-5 terms\"], "
       "\"relevance\": <0-5>, \"idea\": {\"text\": \"<one testable idea using daily columns gex_rank and y_range>\", \"testable\": true}}")
QSYS = ("Turn this question into a JSON test spec: {\"kind\":\"question\",\"question\":\"...\",\"target\":\"<formula using y_ columns>\","
        "\"expr\":\"<formula using k_ columns only>\"}. Columns: k_gap (gap %), k_on_range (overnight range %), y_range (session range %), "
        "y_up (1 if the session closed up). Reply ONLY with JSON.")
Q = "Do sessions after a big overnight range have a bigger range?"
url = L.worker_url()
for m in ["@cf/meta/llama-4-scout-17b-16e-instruct", "@cf/openai/gpt-oss-120b", "@cf/openai/gpt-oss-20b", "@cf/qwen/qwen3-30b-a3b-fp8"]:
    for name, s, u, mt in (("read", SYS, PAPER, 700), ("spec", QSYS, Q, 400)):
        t = time.time()
        try:
            L.COST.setdefault(m, (30, 70))
            out, units = L._call(url, m, s, u, mt)
            try: j = T.first_json(out); ok = "JSON ok"
            except Exception: j = {}; ok = "BAD JSON"
            print(f"{m.split('/')[-1]:34s} {name}: {ok}, {time.time()-t:4.1f}s, ~{units:.1f} units | {json.dumps(j)[:260]}")
        except Exception as e:
            body = e.read().decode()[:200] if hasattr(e, "read") else ""
            print(f"{m.split('/')[-1]:34s} {name}: FAILED {type(e).__name__} {str(e)[:80]} {body}")
