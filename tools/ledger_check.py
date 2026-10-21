"""tools/ledger_check.py - fails LOUDLY if a ledger that must only grow was rewritten (expert review 2, integrity).

The records that keep Volta honest must never silently revert (a concurrent job's `git rebase -X theirs` once did exactly
that to review lines). Checked against the last good checkpoint (knowledge/ledgers/checkpoints.json, hash chain):
  * strategies.jsonl - append-only: the first N lines must hash to the recorded value
  * ledgers/exams/   - one file per spent exam: no file may disappear
  * families_ledger.csv - rows never disappear; a family's frozen commit, p-value and alpha never change
Each checkpoint stores the hash of the previous checkpoint (a chain). A break -> Discord announcement + exit code 1
(the workflow run turns red). On success the checkpoint moves forward."""
import hashlib, json, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); K = os.path.join(HERE, "knowledge")
CP = os.path.join(K, "ledgers", "checkpoints.json")


def _h(b): return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def state():
    st = {}
    p = os.path.join(K, "strategies.jsonl"); lines = open(p, "rb").read().splitlines() if os.path.exists(p) else []
    st["strategies"] = {"lines": len(lines), "sha": _h(b"\n".join(lines))}
    d = os.path.join(K, "ledgers", "exams"); st["exams"] = sorted(os.listdir(d)) if os.path.isdir(d) else []
    try:
        import pandas as pd
        L = pd.read_csv(os.path.join(K, "families_ledger.csv"))
        st["families"] = {r.family: _h(f"{r.frozen}|{r.p}|{r.alpha}") for r in L.itertuples()}
    except Exception:
        st["families"] = {}
    return st


def check():
    cur = state(); errs = []
    if not os.path.exists(CP): return cur, errs, None
    chain = json.load(open(CP)); last = chain[-1]["state"]
    p = os.path.join(K, "strategies.jsonl"); lines = open(p, "rb").read().splitlines() if os.path.exists(p) else []
    n = last["strategies"]["lines"]
    if len(lines) < n or _h(b"\n".join(lines[:n])) != last["strategies"]["sha"]:
        errs.append(f"strategies.jsonl was rewritten (first {n} lines changed or removed)")
    gone = sorted(set(last["exams"]) - set(cur["exams"]))
    if gone: errs.append(f"{len(gone)} spent-exam records disappeared: {gone[:3]}")
    for f, h in last["families"].items():
        if f not in cur["families"]: errs.append(f"family {f} vanished from families_ledger.csv")
        elif cur["families"][f] != h: errs.append(f"family {f}: frozen commit / p-value / alpha changed after scoring")
    return cur, errs, chain


def main():
    cur, errs, chain = check()
    if errs:
        print("LEDGER INTEGRITY BROKEN:\n- " + "\n- ".join(errs))
        sys.path.insert(0, HERE)
        try:
            import test_engine as TE
            ann = json.load(open(TE.ANN)) if os.path.exists(TE.ANN) else []
            ann.append({"title": "🚨 Ledger integrity check FAILED", "body": "\n".join(errs)[:1500]
                        + "\nA record that must only grow was rewritten. Claude restores it from git history before anything else runs."})
            json.dump(ann, open(TE.ANN, "w"), indent=1)
        except Exception as e:
            print("announcement failed:", e)
        sys.exit(1)
    chain = chain or []
    prev = _h(json.dumps(chain[-1], sort_keys=True)) if chain else "genesis"
    chain.append({"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prev": prev, "state": cur})
    os.makedirs(os.path.dirname(CP), exist_ok=True); json.dump(chain[-50:], open(CP, "w"), indent=0)
    print("ledgers OK:", cur["strategies"]["lines"], "strategy lines,", len(cur["exams"]), "exam records,", len(cur["families"]), "families")


if __name__ == "__main__":
    main()
