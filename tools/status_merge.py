"""tools/status_merge.py - merges status.json KEY BY KEY when two jobs changed it at the same time.

Why (plain words): about 20 jobs each write their own entry into status.json (the snapshot the Discord commands read).
When two jobs finished close together, git had to combine two versions of the whole file line by line, and with
`-X theirs` the later job could overwrite another job's fresh entry with its own stale copy. This script replaces that
line-by-line guess with a rule that cannot lose anything:

    for every entry (key): whoever CHANGED it since the common starting point wins;
    if both changed the same entry, the job that is committing right now wins (same as before);
    entries nobody touched stay as they are.

git calls it automatically (see .gitattributes and .github/actions_common.sh):
    python3 tools/status_merge.py <ancestor> <upstream> <this-run>
The result is written over <upstream> (git's rule for merge drivers). Exit code 0 = merged; anything else = git falls
back to its normal conflict handling, so a broken file can never make things worse than before.
Self-check: python3 tools/status_merge.py --selftest"""
import json, sys

_MISSING = object()


def merge(base, ours, theirs):
    """3-way merge of three dicts. `theirs` (the run that is committing now) wins when both sides changed a key."""
    out = {}
    for k in list(ours) + [k for k in theirs if k not in ours] + [k for k in base if k not in ours and k not in theirs]:
        b, o, t = base.get(k, _MISSING), ours.get(k, _MISSING), theirs.get(k, _MISSING)
        if o is _MISSING and t is _MISSING: continue                 # deleted on both sides
        if _same(o, t): v = o                                        # both sides agree
        elif _same(o, b): v = t                                      # only this run changed (or deleted) it
        elif _same(t, b): v = o                                      # only upstream changed (or deleted) it
        else: v = t if t is not _MISSING else o                      # both changed: this run wins; never drop data for a delete
        if v is not _MISSING: out[k] = v
    return out


def _same(a, b):
    if a is _MISSING or b is _MISSING: return a is b
    return a == b


def _load(path):
    txt = open(path, encoding="utf-8").read()
    d = json.loads(txt) if txt.strip() else {}
    if not isinstance(d, dict): raise ValueError("status.json must be an object")
    return d


def _selftest():
    base = {"a": 1, "b": [1], "c": "x", "gone": 1}
    ours = {"a": 2, "b": [1], "c": "x", "gone": 1, "new_up": 5}       # upstream changed a, added new_up
    theirs = {"a": 1, "b": [2], "c": "x", "new_run": 7}               # this run changed b, deleted gone, added new_run
    m = merge(base, ours, theirs)
    assert m == {"a": 2, "b": [2], "c": "x", "new_up": 5, "new_run": 7}, m
    assert merge({"k": 1}, {"k": 2}, {"k": 3}) == {"k": 3}            # both changed -> this run wins
    assert merge({"k": 1}, {"k": 2}, {}) == {"k": 2}                  # changed upstream, deleted here -> keep the data
    assert merge({}, {}, {}) == {}
    assert list(merge({"a": 1, "b": 1}, {"a": 1, "b": 2}, {"a": 3, "b": 1})) == ["a", "b"]   # key order stays stable
    print("status_merge selftest OK")


def main():
    if "--selftest" in sys.argv: _selftest(); return 0
    if len(sys.argv) < 4:
        print(__doc__); return 2
    anc, cur, oth = sys.argv[1:4]
    try:
        base = _load(anc)
    except Exception:
        base = {}                                                    # no usable ancestor: treat every key as new
    try:
        ours, theirs = _load(cur), _load(oth)
    except Exception as e:
        print("status_merge: cannot read a side:", type(e).__name__, e); return 1
    merged = merge(base, ours, theirs)
    with open(cur, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1)                               # same layout the jobs write (indent=1, no final newline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
