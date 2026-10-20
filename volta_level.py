"""volta_level.py - Volta's level: one number that only goes up when Volta really got better.
XP comes from verified progress, not activity alone:
  +1 per paper read, +2 per idea/strategy tested, +5 per strategy that stayed positive on unseen 2022-23 (prop search),
  +30 per brain upgrade that beat the old brain on unseen days, +50 per self-discovered power, +200 per strategy that
  passed the locked exam, +300 per strategy with positive live forward results. Level = 1 + floor(sqrt(XP / 40)).
Runs every evening; posts when Volta levels up and what got it there."""
import json, math, os, sys
from datetime import datetime, timezone
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
LOG, STATUS = os.path.join(K, "level.csv"), os.path.join(HERE, "status.json")


def _jl(f):
    p = os.path.join(K, f); return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def stats():
    s = {}
    s["papers"] = len(_jl("library.jsonl"))
    s["tests"] = len(_jl("questions.jsonl")) + len(_jl("strategies.jsonl"))
    try:
        import prop_search as PS
        A = PS.all_results(); s["searched"] = len(A); s["validated"] = int((A.get("ev_val", pd.Series(dtype=float)) > 0).sum()) if len(A) else 0
        s["best_val_ev"] = round(float(A.ev_val.max()), 1) if len(A) and "ev_val" in A and A.ev_val.notna().any() else None
    except Exception:
        s["searched"] = s["validated"] = 0; s["best_val_ev"] = None
    S = _jl("strategies.jsonl"); s["exam_passed"] = sum(str(e.get("verdict", "")).startswith("PROMISING STRATEGY") for e in S)
    p = os.path.join(K, "discovered_powers.json"); s["powers"] = len(json.load(open(p))) if os.path.exists(p) else 0
    try:
        import brain
        m = json.load(open(brain.MODEL)); s["brain_upgrades"] = int(str(m.get("version", "1.0")).split(".")[1])
    except Exception:
        s["brain_upgrades"] = 0
    f = os.path.join(K, "strategy_forward.csv")
    try:
        F = pd.read_csv(f); g = F[F.traded].groupby("id").R.sum(); s["live_winners"] = int((g > 0).sum())
    except Exception:
        s["live_winners"] = 0
    s["xp"] = (s["papers"] + 2 * s["tests"] + 5 * s["validated"] + 30 * s["brain_upgrades"] + 50 * s["powers"]
               + 200 * s["exam_passed"] + 300 * s["live_winners"])
    s["level"] = 1 + int(math.sqrt(s["xp"] / 40))
    return s


def main():
    s = stats(); today = datetime.now(timezone.utc).date().isoformat()
    H = pd.read_csv(LOG) if os.path.exists(LOG) else pd.DataFrame()
    prev = H.iloc[-1].to_dict() if len(H) else None
    H = pd.concat([H[H.date != today] if len(H) else H, pd.DataFrame([{"date": today, **s}])], ignore_index=True); H.to_csv(LOG, index=False)
    nxt = 40 * (s["level"]) ** 2
    lines = [f"VOLTA LEVEL {s['level']}  ({s['xp']:,} XP, next level at {nxt:,})",
             f"Papers read {s['papers']} | ideas & strategies tested {s['tests']} | prop strategies searched {s['searched']:,}",
             f"Survived unseen 2022-23: {s['validated']} (best EV per eval {s['best_val_ev'] if s['best_val_ev'] is not None else '-'})"
             f" | passed the locked exam: {s['exam_passed']} | live winners: {s['live_winners']}",
             f"Brain upgrades: {s['brain_upgrades']} | self-discovered powers: {s['powers']}",
             "XP only for verified progress: tests passed on unseen data count far more than activity."]
    if prev is not None:
        d = {k: s[k] - prev.get(k, 0) for k in ("papers", "tests", "validated", "brain_upgrades", "powers", "exam_passed", "live_winners")
             if isinstance(s.get(k), (int, float)) and s[k] - (prev.get(k) or 0) > 0}
        if d: lines.append("Since yesterday: " + ", ".join(f"+{v} {k.replace('_', ' ')}" for k, v in d.items()))
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    st["level"] = lines; json.dump(st, open(STATUS, "w"), indent=1)
    print("\n".join(lines))
    if prev is not None and s["level"] > int(prev.get("level", 1)):
        try:
            import test_engine as T
            ann = json.load(open(T.ANN)) if os.path.exists(T.ANN) else []
            ann.append({"title": f"⬆️ Volta reached level {s['level']}", "body": "\n".join(lines)}); json.dump(ann, open(T.ANN, "w"), indent=1)
        except Exception as e:
            print("announce skipped:", e)


if __name__ == "__main__":
    main()
