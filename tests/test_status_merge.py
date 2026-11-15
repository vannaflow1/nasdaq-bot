import json, os, subprocess, sys, tempfile, unittest
from _util import ROOT
import status_merge as SM


class MergeRules(unittest.TestCase):
    def test_each_side_keeps_what_it_changed(self):
        base = {"bias": ["old"], "eta": ["old"], "news": ["old"]}
        upstream = {"bias": ["NEW from the bias job"], "eta": ["old"], "news": ["old"]}
        this_run = {"bias": ["old"], "eta": ["NEW from the search job"], "news": ["old"]}     # stale copy of bias
        m = SM.merge(base, upstream, this_run)
        self.assertEqual(m, {"bias": ["NEW from the bias job"], "eta": ["NEW from the search job"], "news": ["old"]})

    def test_same_key_changed_twice_this_run_wins(self):
        self.assertEqual(SM.merge({"k": 1}, {"k": 2}, {"k": 3}), {"k": 3})

    def test_new_keys_from_both_sides_survive(self):
        self.assertEqual(SM.merge({}, {"a": 1}, {"b": 2}), {"a": 1, "b": 2})

    def test_delete_is_respected_only_if_other_side_did_not_change_it(self):
        self.assertEqual(SM.merge({"k": 1, "x": 0}, {"k": 1, "x": 0}, {"x": 0}), {"x": 0})       # deleted here, untouched upstream
        self.assertEqual(SM.merge({"k": 1}, {"k": 2}, {}), {"k": 2})                            # upstream changed it: keep the data

    def test_command_line_writes_result_over_upstream_file(self):
        d = tempfile.mkdtemp()
        paths = [os.path.join(d, n) for n in ("base", "ours", "theirs")]
        for p, v in zip(paths, ({"a": 1, "b": 1}, {"a": 2, "b": 1}, {"a": 1, "b": 3})): json.dump(v, open(p, "w"), indent=1)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "status_merge.py"), *paths])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.load(open(paths[1])), {"a": 2, "b": 3})

    def test_broken_file_reports_failure_instead_of_guessing(self):
        d = tempfile.mkdtemp(); paths = [os.path.join(d, n) for n in ("base", "ours", "theirs")]
        open(paths[0], "w").write("{}"); open(paths[1], "w").write("{not json"); open(paths[2], "w").write("{}")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "status_merge.py"), *paths], capture_output=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(paths[1]).read(), "{not json")                                   # left untouched


if __name__ == "__main__":
    unittest.main()
