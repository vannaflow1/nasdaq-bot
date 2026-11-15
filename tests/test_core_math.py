import json, os, unittest
from datetime import date
import numpy as np
from _util import ROOT
import families as F, sealed, outlook, eta

K = os.path.join(ROOT, "knowledge")


class Statistics(unittest.TestCase):
    def test_p_value_is_never_zero_and_counts_ties(self):
        null = np.arange(100.0)
        self.assertAlmostEqual(F.null_p(1000, null), 1 / 101)             # nothing as extreme: smallest possible p, not 0
        self.assertAlmostEqual(F.null_p(-1, null), 1.0)
        self.assertAlmostEqual(F.null_p(90, null), (1 + 10) / 101)        # 90..99 are at least as extreme
        self.assertAlmostEqual(F.null_p(5, [np.nan, 1, 9]), (1 + 1) / 3)  # NaN draws are dropped

    def test_sequential_boundaries_get_easier_and_end_above_a_single_test(self):
        b = sealed.obf_bounds()
        self.assertEqual(len(b), 10); self.assertEqual(b, sorted(b, reverse=True))
        self.assertTrue(1.645 < b[-1] < 2.0, b[-1])                       # stricter than one look at 5% one-sided (1.645)


class Timer(unittest.TestCase):
    def test_timer_belief_matches_the_official_forward_numbers(self):
        fams = {f["id"]: f for f in json.load(open(os.path.join(K, "families.json")))}
        for fam in eta.FAMILIES:
            fw = fams[fam].get("forward") or {}
            if not fw.get("n"): continue
            d = eta._design(fam); rate, sd, sd_post = eta._params(fam, d)
            mu, s = eta._posterior(d, int(fw["n"]), float(fw["edge"]), sd_post)
            self.assertAlmostEqual(mu, fw["posterior_mean"], delta=0.002, msg=fam)
            self.assertAlmostEqual(s, fw["posterior_sd"], delta=0.002, msg=fam)

    def test_f10_inputs_are_the_declared_ones_and_f13_come_from_its_own_design(self):
        d10, d13 = eta._design("F10"), eta._design("F13")
        self.assertEqual(eta._params("F10", d10), (0.98, 2.07, 2.07))
        rate, sd, sd_post = eta._params("F13", d13)
        self.assertEqual(sd, d13["futility"]["cp_sd_per_trade_R"]); self.assertEqual(sd_post, max(sd, 1.5))
        self.assertAlmostEqual(rate, d13["posterior"]["validation"]["n"] / 1011)
        self.assertAlmostEqual(d10["posterior"]["validation"]["n"] / eta.VAL_DAYS, 0.98, places=2)   # where 1011 comes from


class Clocks(unittest.TestCase):
    def test_london_open_in_chicago_time_including_the_mismatch_weeks(self):
        self.assertEqual(outlook.lon_open_ct(date(2026, 11, 10)), 120)    # winter: 08:00 London = 02:00 Chicago
        self.assertEqual(outlook.lon_open_ct(date(2026, 7, 1)), 120)      # summer: both on summer time
        self.assertEqual(outlook.lon_open_ct(date(2026, 10, 27)), 180)    # Europe already back, US not yet
        self.assertEqual(outlook.lon_open_ct(date(2027, 3, 16)), 180)     # US already forward, Europe not yet

    def test_day_size_table_is_ordered(self):
        names = [s[0] for s in outlook.SIZE]
        self.assertEqual(names, ["QUIET", "CALMER", "NORMAL", "BUSIER", "WIDE"])
        self.assertEqual(outlook.CUTS, sorted(outlook.CUTS)); self.assertEqual(len(outlook.CUTS), len(outlook.SIZE) - 1)
        self.assertLess(outlook.SIZE[0][2], outlook.SIZE[-1][2])           # WIDE days expect a bigger range than QUIET days


if __name__ == "__main__":
    unittest.main()
