"""gemini.py - small client for Google's Gemini API (free tier), used by gemini_agent.py.

Key: GitHub secret GEMINI_API_KEY (whitespace/quotes stripped automatically - the stored secret has a stray character).
Models: tried in order; 503 "high demand" and 429 quota errors fall through to the next model after a short retry.
The Pro models have no free quota on this key (checked 2026-10-21), so only Flash models are used.
Every call is counted in knowledge/gemini_budget.json (resets daily, UTC) so a run can never burn the free quota."""
import json, os, time, urllib.error, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = os.path.join(HERE, "knowledge", "gemini_budget.json")
BASE = "https://generativelanguage.googleapis.com/v1beta"
MODELS = [m.strip() for m in os.environ.get("GEMINI_MODELS", "gemini-3.8-flash,gemini-flash-latest,gemini-flash-lite-latest").split(",") if m.strip()]
DAILY_CALLS = int(os.environ.get("GEMINI_DAILY_CALLS", "120"))


class GeminiError(Exception):
    pass


def key():
    k = os.environ.get("GEMINI_API_KEY", "")
    k = "".join(k.split()).strip("'\"")
    if not k:
        raise GeminiError("GEMINI_API_KEY is not set")
    return k


def _budget(add=0, model=None):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        b = json.load(open(BUDGET))
    except Exception:
        b = {}
    if b.get("day") != day:
        b = {"day": day, "calls": 0, "by_model": {}}
    if add:
        b["calls"] += add
        if model: b["by_model"][model] = b["by_model"].get(model, 0) + add
        json.dump(b, open(BUDGET, "w"), indent=1)
    return b


def calls_left():
    return DAILY_CALLS - _budget()["calls"]


def _post(model, body, timeout=180):
    req = urllib.request.Request(f"{BASE}/models/{model}:generateContent", data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        return e.code, {"error": msg[:300]}
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {e}"[:300]}


def generate(contents, system=None, tools=None, temperature=0.2, max_tokens=8192):
    """One generateContent call with model fallback. Returns (model_used, candidate_content_dict).
    The returned content is passed back VERBATIM in the next turn (Gemini 3 needs its thought signatures)."""
    if calls_left() <= 0:
        raise GeminiError(f"daily Gemini budget used up ({DAILY_CALLS} calls)")
    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools
    errors = []
    for model in MODELS:
        for attempt in range(3):
            st, js = _post(model, body)
            _budget(1, model)
            if st == 200:
                cands = js.get("candidates") or []
                if not cands or "content" not in cands[0]:
                    errors.append(f"{model}: empty answer ({(cands[0].get('finishReason') if cands else js.get('promptFeedback'))})")
                    break
                return model, cands[0]["content"]
            errors.append(f"{model}: HTTP {st} {js.get('error', '')[:120]}")
            if st in (429, 500, 503, -1) and attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            break                      # 400/404 etc.: this model will not work - try the next one
    raise GeminiError("all Gemini models failed: " + " | ".join(errors[-4:]))


def ask(prompt, system=None, **kw):
    """Plain text question -> text answer."""
    _, c = generate([{"role": "user", "parts": [{"text": prompt}]}], system=system, **kw)
    return "".join(p.get("text", "") for p in c.get("parts", []) if not p.get("thought"))


if __name__ == "__main__":
    print(ask("Reply with exactly: OK"))
    print("calls left today:", calls_left())
