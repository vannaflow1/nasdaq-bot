import os, tempfile, unittest
import pandas as pd
from _util import ROOT
import prop_search as PS


class Parking(unittest.TestCase):
    def test_small_file_is_used_as_is(self):
        d = tempfile.mkdtemp(); res = os.path.join(d, "results_0.csv")
        pd.DataFrame({"spec_id": ["a", "b"], "x": [1, 2]}).to_csv(res, index=False)
        R = PS._park_full_results(res, limit=10 ** 9)
        self.assertEqual(len(R), 2); self.assertEqual(os.listdir(d), ["results_0.csv"])

    def test_full_file_is_parked_and_everything_is_still_read(self):
        d = tempfile.mkdtemp(); res = os.path.join(d, "results_0.csv")
        pd.DataFrame({"spec_id": ["a", "b"], "x": [1, 2]}).to_csv(res, index=False)
        R = PS._park_full_results(res, limit=5)
        self.assertEqual((len(R), list(R.columns)), (0, ["spec_id", "x"]))                 # fresh table, same columns
        pd.concat([R, pd.DataFrame({"spec_id": ["c"], "x": [3]})]).to_csv(res, index=False)
        PS._park_full_results(res, limit=5)                                                 # second park gets the next number
        self.assertEqual(sorted(os.listdir(d)), ["results_0_part1.csv", "results_0_part2.csv"])
        old = PS.OUT
        try:
            PS.OUT = d; self.assertEqual(sorted(PS.all_results().spec_id), ["a", "b", "c"])
        finally:
            PS.OUT = old

    def test_missing_file_gives_an_empty_table(self):
        self.assertEqual(len(PS._park_full_results(os.path.join(tempfile.mkdtemp(), "none.csv"))), 0)

    def test_limit_is_safely_below_githubs_100_mb(self):
        self.assertLess(PS.PARK_BYTES, 95 * 1024 * 1024)

    def test_no_live_results_file_in_the_repo_is_over_githubs_limit(self):
        import glob
        for f in glob.glob(os.path.join(ROOT, "knowledge", "prop_search", "results_*.csv")):
            self.assertLess(os.path.getsize(f), 100 * 1024 * 1024, f)


if __name__ == "__main__":
    unittest.main()
