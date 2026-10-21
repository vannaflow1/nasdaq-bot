"""gemini_agent.py - Volta's free coding agent (Google Gemini, free tier), run nightly by .github/workflows/gemini-agent.yml.

It takes ONE open wish from knowledge/wishlist.json and tries to build it on the RESEARCH side only, with tools to read,
search, edit files and run scripts. It never touches main directly: an accepted draft is committed to a branch
gemini/wish-<id>; Claude's nightly upgrade session reviews that branch and merges it (or rejects it with a reason).

Guardrails (checked by this script, not by the model):
  - only research-side files may change (ALLOWED below); no deletions; at most MAX_LINES changed lines;
  - every changed .py must compile and import; `python test_engine.py` (the engine self-test) must still pass;
  - the commands the model may run are restricted, run without any secret in their environment, with a timeout;
  - the Gemini key is never written anywhere; the git checkout has no push credentials while the model works.
Run by hand: GEMINI_WISH=<id> python gemini_agent.py   or   GEMINI_TASK="<free text>" python gemini_agent.py (test task)
"""
import fnmatch, json, os, re, shlex, subprocess, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gemini

K = os.path.join(HERE, "knowledge")
WISH = os.path.join(K, "wishlist.json"); DRAFTS = os.path.join(K, "gemini_drafts.json")
RESULT = os.environ.get("GEMINI_RESULT", "/tmp/gemini_result.json")
MAX_STEPS = int(os.environ.get("GEMINI_MAX_STEPS", "40")); MAX_MIN = float(os.environ.get("GEMINI_MAX_MINUTES", "45")); MAX_LINES = int(os.environ.get("GEMINI_MAX_LINES", "600"))
RESEARCH_FILES = ["test_engine.py", "idea_lab.py", "strategy_lab.py", "strategy_forward.py", "prop_sim.py", "prop_search.py",
                  "discovered_read.py", "introspect.py", "learn_fetch.py", "learn_read.py", "learn_post.py", "fetch_macro.py",
                  "spx_collect.py", "vault.py", "volta_book.py", "volta_level.py", "pool_review.py"]
ALLOWED = RESEARCH_FILES + ["tools/*.py", "atlas/*.py", "knowledge/research_out/*", "knowledge/prop_firms.json", "knowledge/papers/*.md"]
LIVE = ["nasdaq_bot.py", "brain.py", "brain_model.json", "live_tracker.py", "volflag.py", "levels.py", "options_nerd.py", "plan.py",
        "spx_morning.py", "register_commands.py", "models/*", "worker/*", ".github/*", "requirements.txt", "gemini.py", "gemini_agent.py"]
OWN_STATE = ["knowledge/gemini_budget.json", "knowledge/gemini_drafts.json", "knowledge/wishlist.json",
             "knowledge/research_out/gemini_agent_last.log", "knowledge/research_out/gemini_agent_progress.log"]
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sh(cmd, timeout=600, env=None):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=HERE, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, (p.stdout + p.stderr)


def clean_env():
    """Environment for anything the model runs: no secrets at all."""
    env = {k: v for k, v in os.environ.items()
           if not re.search(r"KEY|TOKEN|SECRET|PASS|WEBHOOK|CF_|DISCORD|GITHUB_|ACTIONS_", k, re.I)}
    env["PYTHONPATH"] = HERE
    return env


def norm(path):
    return os.path.normpath(path).lstrip("./") if path not in (".", "./") else "."


def allowed(path):
    path = norm(path)
    if path.startswith("..") or os.path.isabs(path): return False
    if any(fnmatch.fnmatch(path, p) for p in LIVE): return False
    if any(fnmatch.fnmatch(path, p) for p in ALLOWED): return True
    return "/" not in path and path.endswith(".py") and (path in NEW_FILES or not os.path.exists(os.path.join(HERE, path)))


NEW_FILES = set()      # new root scripts the model created this run (may be edited again)


def safe(path):
    p = os.path.normpath(os.path.join(HERE, path))
    if p != HERE and not p.startswith(HERE + os.sep) or "/.git" in p: raise ValueError("path outside the repo")
    return p


# ------------------------------------------------------------------ tools the model can call
def t_list_dir(path="."):
    p = safe(path)
    if not os.path.isdir(p): return f"not a directory: {path}"
    items = sorted(os.listdir(p))
    return "\n".join((i + "/" if os.path.isdir(os.path.join(p, i)) else f"{i}  ({os.path.getsize(os.path.join(p, i))} bytes)")
                     for i in items if i != ".git")[:8000]


def t_read_file(path, start_line=1, max_lines=250):
    p = safe(path)
    if not os.path.isfile(p): return f"no such file: {path}"
    L = open(p, errors="replace").read().splitlines(); s = max(1, int(start_line)); n = max(1, min(int(max_lines), 400))
    body = "\n".join(f"{i}: {l[:400]}" for i, l in enumerate(L[s - 1:s - 1 + n], s))
    return f"{path} ({len(L)} lines; showing {s}-{min(len(L), s + n - 1)})\n{body}"


def t_search(pattern, path_glob="*.py"):
    rc, out = sh(["grep", "-rnE", "--include", path_glob, "--exclude-dir=.git", "--exclude-dir=data", pattern, "."], timeout=60)
    lines = out.splitlines()
    return ("\n".join(l[:300] for l in lines[:80]) + (f"\n... {len(lines) - 80} more" if len(lines) > 80 else "")) or "no match"


def t_write_file(path, content):
    if not allowed(path):
        return f"REFUSED: {path} is not a research-side file you may write (allowed: {', '.join(ALLOWED)}, or a new root .py script)"
    p = safe(path)
    if "/" not in norm(path) and not os.path.exists(p): NEW_FILES.add(norm(path))
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(content)
    return f"wrote {path} ({len(content.splitlines())} lines)"


def t_edit_file(path, old, new):
    if not allowed(path): return f"REFUSED: {path} is not a research-side file you may edit"
    p = safe(path)
    if not os.path.isfile(p): return f"no such file: {path}"
    s = open(p).read(); n = s.count(old)
    if n != 1: return f"old text found {n} times in {path} - it must match exactly once (copy it exactly, include more context)"
    open(p, "w").write(s.replace(old, new, 1)); return f"edited {path}"


def t_run(command):
    try: parts = shlex.split(command)
    except ValueError as e: return f"REFUSED: {e}"
    if parts and parts[0] in ("python", "python3") and len(parts) >= 3 and parts[1:3] == ["-m", "py_compile"]: pass
    elif parts and parts[0] in ("python", "python3") and len(parts) >= 2 and parts[1].endswith(".py") and os.path.isfile(safe(parts[1])):
        if any(fnmatch.fnmatch(norm(parts[1]), p) for p in LIVE):
            return "REFUSED: live-side scripts may not be run (they can post to Discord)"
    else:
        return "REFUSED: only `python <existing script>.py [args]` and `python -m py_compile <file>` may be run"
    env = clean_env(); env.setdefault("SEARCH_MINUTES", "1"); env.setdefault("PORTFOLIO_MINUTES", "1"); env["VOLTA_DRY"] = "1"
    try: rc, out = sh(["python"] + parts[1:], timeout=900, env=env)
    except subprocess.TimeoutExpired: return "TIMEOUT after 15 minutes"
    return f"exit code {rc}\n" + out[-6000:]


TOOLS = {"list_dir": t_list_dir, "read_file": t_read_file, "search": t_search, "write_file": t_write_file,
         "edit_file": t_edit_file, "run": t_run, "finish": lambda summary="", how_to_use="": "FINISH",
         "give_up": lambda reason="": "GIVE_UP"}
S, I = {"type": "string"}, {"type": "integer"}
DECL = [{"functionDeclarations": [
    {"name": "list_dir", "description": "List a directory of the repo.", "parameters": {"type": "object", "properties": {"path": S}}},
    {"name": "read_file", "description": "Read lines of a file (numbered). Use start_line to page through long files.",
     "parameters": {"type": "object", "properties": {"path": S, "start_line": I, "max_lines": I}, "required": ["path"]}},
    {"name": "search", "description": "grep -E a regex over the repo (default only *.py files).",
     "parameters": {"type": "object", "properties": {"pattern": S, "path_glob": S}, "required": ["pattern"]}},
    {"name": "write_file", "description": "Create or fully overwrite a research-side file.",
     "parameters": {"type": "object", "properties": {"path": S, "content": S}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace one exact, unique piece of text in a file.",
     "parameters": {"type": "object", "properties": {"path": S, "old": S, "new": S}, "required": ["path", "old", "new"]}},
    {"name": "run", "description": "Run `python <script>.py [args]` (15 min limit, no secrets, no Discord) or `python -m py_compile <file>`.",
     "parameters": {"type": "object", "properties": {"command": S}, "required": ["command"]}},
    {"name": "finish", "description": "Call when the wish is built AND you ran it successfully. Summary = what changed, real results only.",
     "parameters": {"type": "object", "properties": {"summary": S, "how_to_use": S}, "required": ["summary"]}},
    {"name": "give_up", "description": "Call if the wish needs live-side files, money, accounts, data you cannot get, or you cannot make it work.",
     "parameters": {"type": "object", "properties": {"reason": S}, "required": ["reason"]}}]}]

SYSTEM = """You are Volta's coding agent. Volta is an automated research + prop-trading bot (Python, GitHub Actions) in this repo.
You build ONE wish Volta filed for itself, on the RESEARCH side only, then stop. A senior reviewer (Claude) checks your branch
before anything is merged, so be careful and honest.
Rules:
- Read before you write: look at the files the wish concerns and how similar things are already done in this repo.
- You may only change research-side files: {allowed}, or add a NEW root .py script. Never live-side files ({live}).
- Keep changes small and in the existing style. Do not reformat or rewrite code you do not need to change. No new pip packages
  beyond pandas, numpy, scipy, scikit-learn, pyarrow, arch. Scripts in tools/ can import root modules (PYTHONPATH is the repo).
- Never weaken a test, guardrail, leak guard, locked exam, placebo or luck control. Never look into the future (no lookahead).
- Never invent results or numbers. Only report numbers that your `run` calls actually printed.
- Run what you built (`run`), fix errors, and run `python test_engine.py` at the end (it must exit 0).
- Scripts with a long search loop: keep test runs short (env SEARCH_MINUTES=1 / PORTFOLIO_MINUTES=1 are set for you).
- When done call finish(summary, how_to_use). If impossible or it needs the live side/money/accounts/owner data, call give_up(reason).
You have at most {steps} tool calls."""


# ------------------------------------------------------------------ wish selection
def pick_wish(W):
    if os.environ.get("GEMINI_TASK"):
        return {"id": "task", "title": os.environ["GEMINI_TASK"][:80], "why": os.environ["GEMINI_TASK"], "evidence": "", "type": "code"}
    if os.environ.get("GEMINI_WISH"):
        return next((w for w in W if str(w["id"]) == os.environ["GEMINI_WISH"]), None)
    rank = {"high": 0, "medium": 1, "low": 2}
    cands = []
    for w in W:
        g = w.get("gemini") or {}
        if w.get("status") not in ("open", "approved") or w.get("for") not in ("claude", "gemini", None): continue
        if g.get("status") == "drafted": continue                                   # waiting for Claude's review
        if g.get("attempts", 0) >= 2: continue                                       # tried twice already - leave it to Claude
        cands.append((0 if w.get("for") == "gemini" else 1, rank.get(w.get("impact"), 1), -w.get("votes", 1), str(w.get("date")), w))
    return sorted(cands, key=lambda c: c[:4])[0][-1] if cands else None


def status_files():
    rc, out = sh(["git", "status", "--porcelain", "--untracked-files=all"])
    return {l[3:].strip().strip('"'): l[:2] for l in out.splitlines()}


def model_changes(before):
    """Files changed during this run, excluding the agent's own state files and anything dirty before it started."""
    now = status_files()
    return [(st, f) for f, st in now.items() if f not in OWN_STATE and before.get(f) != st]


def guard(before):
    """Return (ok, reason, files)."""
    files = model_changes(before)
    if not files: return False, "no files changed", []
    bad = [f for st, f in files if not (allowed(f) or any(fnmatch.fnmatch(f, p) for p in ALLOWED))]
    if bad: return False, "touched files outside the research side: " + ", ".join(bad), files
    if any("D" in st for st, f in files): return False, "deleted files: " + ", ".join(f for st, f in files if "D" in st), files
    n = 0
    for st, f in files:
        if st.strip() == "??": n += sum(1 for _ in open(os.path.join(HERE, f), errors="replace"))
        else:
            rc, out = sh(["git", "diff", "--numstat", "--", f])
            n += sum(int(a) + int(b) for a, b, *_ in (l.split("\t") for l in out.splitlines()) if a.isdigit() and b.isdigit())
    if n > MAX_LINES: return False, f"{n} changed lines (limit {MAX_LINES}) - too big for an unreviewed draft", files
    env = clean_env()
    for st, f in files:
        if f.endswith(".py"):
            rc, out = sh(["python", "-m", "py_compile", f], env=env)
            if rc: return False, f"{f} does not compile: {out[-300:]}", files
            if "/" not in f or f.startswith("tools/"):
                mod = f[:-3].replace("/", ".")
                rc, out = sh(["python", "-c", f"import sys; sys.argv=['x']; import importlib; importlib.import_module('{mod}')"],
                             timeout=300, env=env)
                if rc: return False, f"{f} fails on import: {out[-400:]}", files
    rc, out = sh(["python", "test_engine.py"], timeout=1200, env=env)
    if rc: return False, f"test_engine.py self-test fails: {out[-400:]}", files
    return True, f"{len(files)} files, {n} changed lines, compiles, imports, test_engine self-test passes", files


def undo(files):
    for st, f in files:
        if st.strip() == "??":
            try: os.remove(os.path.join(HERE, f))
            except OSError: pass
        else: sh(["git", "checkout", "-q", "--", f])


# ------------------------------------------------------------------ main loop
def main():
    W = json.load(open(WISH)) if os.path.exists(WISH) else []
    w = pick_wish(W)
    if not w:
        print("No wish for the Gemini agent today."); json.dump({"status": "none"}, open(RESULT, "w")); return
    print(f"Wish #{w['id']}: {w['title']}")
    before = status_files()
    rc, home = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]); home = home.strip()
    readme = open(os.path.join(K, "README.md")).read()[:6000] if os.path.exists(os.path.join(K, "README.md")) else ""
    files = "\n".join(sorted(f for f in os.listdir(HERE) if f.endswith(".py")))
    task = (f"WISH #{w['id']} (impact {w.get('impact', '?')}): {w['title']}\nWHY: {w.get('why', '')}\nEVIDENCE: {w.get('evidence', '')}\n\n"
            + (f"YOUR PREVIOUS ATTEMPT was rejected by the reviewer: {w['gemini']['review']}\nAvoid that this time.\n\n"
               if (w.get("gemini") or {}).get("review") else "")
            + f"Root scripts:\n{files}\n\nStart of knowledge/README.md:\n{readme}\n\nBuild this wish now.")
    system = SYSTEM.format(allowed=", ".join(ALLOWED), live=", ".join(LIVE), steps=MAX_STEPS)
    contents = [{"role": "user", "parts": [{"text": task}]}]
    outcome, summary, how, log, models = None, "", "", [], set()
    t0 = time.time(); progress = os.path.join(K, "research_out", "gemini_agent_progress.log")
    os.makedirs(os.path.dirname(progress), exist_ok=True); open(progress, "w").write(f"wish #{w['id']}: {w['title']}\n")
    for step in range(MAX_STEPS):
        if time.time() - t0 > MAX_MIN * 60:
            outcome, summary = "out_of_time", f"stopped after {MAX_MIN:.0f} minutes ({step} model turns)"; break
        try:
            model, c = gemini.generate(contents, system=system, tools=DECL, temperature=0.2)
            models.add(model)
        except gemini.GeminiError as e:
            outcome, summary = "error", str(e); break
        contents.append({"role": "model", "parts": c.get("parts", [])})
        calls = [p["functionCall"] for p in c.get("parts", []) if "functionCall" in p]
        if not calls:
            txt = "".join(p.get("text", "") for p in c.get("parts", []))[:500]
            contents.append({"role": "user", "parts": [{"text": "Use the tools. Call finish(...) when done or give_up(...) if impossible."}]})
            log.append(f"{step}: (text) {txt[:120]}"); continue
        resp = []
        for fc in calls:
            name, args = fc.get("name"), fc.get("args") or {}
            try:
                out = TOOLS[name](**args) if name in TOOLS else f"unknown tool {name}"
            except Exception as e:
                out = f"ERROR {type(e).__name__}: {e}"
            log.append(f"{step}: {name}({', '.join(f'{k}={str(v)[:60]!r}' for k, v in args.items() if k not in ('content', 'new', 'old'))}) -> {str(out)[:100]!r}")
            print(log[-1], flush=True)
            with open(progress, "a") as f: f.write(f"[{(time.time() - t0) / 60:.1f} min, {model}] {log[-1]}\n")
            if name == "finish": outcome, summary, how = "finish", args.get("summary", ""), args.get("how_to_use", "")
            if name == "give_up": outcome, summary = "give_up", args.get("reason", "")
            resp.append({"functionResponse": {"name": name, "response": {"result": str(out)[:12000]}}})
        contents.append({"role": "user", "parts": resp})
        if outcome: break
    else:
        outcome, summary = "out_of_steps", f"used all {MAX_STEPS} tool calls without finishing"

    res = {"wish": w["id"], "title": w["title"], "outcome": outcome, "summary": summary[:2000], "how_to_use": how[:1000],
           "date": NOW, "steps": len(log), "models": sorted(models), "calls_left_today": gemini.calls_left()}
    branch = f"gemini/wish-{w['id']}"
    files = model_changes(before)
    if outcome == "finish":
        ok, why, files = guard(before)
        res["guard"] = why
        if ok:
            sh(["git", "checkout", "-q", "-B", branch])
            sh(["git", "add", "--"] + [f for _, f in files])
            sh(["git", "-c", "user.name=Volta Gemini agent", "-c", "user.email=nasdaq-bot@users.noreply.github.com", "commit", "-q", "-m",
                f"Gemini draft for wish #{w['id']}: {w['title'][:60]}\n\n{summary[:1500]}\n\nHow to use: {how[:500]}\nGuard: {why}", "--"] + [f for _, f in files])
            rc, h = sh(["git", "rev-parse", "HEAD"])
            res.update(status="drafted", branch=branch, commit=h.strip(), files=[f for _, f in files])
            sh(["git", "checkout", "-q", home])
        else:
            res["status"] = "rejected by guard"
    else:
        res["status"] = outcome
    undo(model_changes(before))            # main keeps only the agent's own state files
    json.dump(res, open(RESULT, "w"), indent=1)
    if w["id"] != "task":
        W = json.load(open(WISH))
        for x in W:
            if x["id"] == w["id"]:
                g = x.get("gemini") or {}
                x["gemini"] = {"status": res["status"], "date": NOW, "attempts": g.get("attempts", 0) + 1,
                               "branch": res.get("branch"), "summary": res["summary"][:600], "guard": res.get("guard")}
        json.dump(W, open(WISH, "w"), indent=1, ensure_ascii=False)
    D = json.load(open(DRAFTS)) if os.path.exists(DRAFTS) else []
    D.append(res); json.dump(D[-50:], open(DRAFTS, "w"), indent=1, ensure_ascii=False)
    os.makedirs(os.path.join(K, "research_out"), exist_ok=True)
    open(os.path.join(K, "research_out", "gemini_agent_last.log"), "w").write(json.dumps(dict(res, log=log[-80:]), indent=1, ensure_ascii=False))
    print(f"\nWish #{w['id']}: {res['status']} - {res['summary'][:300]}")


if __name__ == "__main__":
    main()
