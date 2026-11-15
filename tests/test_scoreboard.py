import unittest
from datetime import datetime, timedelta
import pandas as pd
from _util import ROOT
import scoreboard as SB


class Counting(unittest.TestCase):
    def test_bias_score_counts_only_graded_long_short_checks(self):
        L = pd.DataFrame({"date": ["2026-11-02"] * 3 + ["2026-11-10"] * 3, "bias": ["LONG", "NONE", "SHORT", "LONG", "SHORT", "LONG"],
                          "result": ["right", "n/a", "wrong", "wrong", "right", None]})
        self.assertEqual(SB.bias_score(L), (2, 4, 2))
        self.assertEqual(SB.bias_score(L, "2026-11-09"), (1, 2, 1))

    def test_real_session_range_from_minute_bars(self):
        rows = []
        for m in range(-30, 420):                                   # 08:00 .. 15:29 Chicago; only 08:30-14:59 may count
            ts = datetime(2026, 11, 10, 8, 30) + timedelta(minutes=m)
            inside = 0 <= m < 390
            rows.append({"ts": ts, "open": 100.0, "high": 110.0 if inside else 500.0, "low": 95.0 if inside else 1.0, "close": 104.0})
        S = SB.rth_stats(pd.DataFrame(rows))
        self.assertEqual(S["2026-11-10"], (100.0, 110.0, 95.0, 104.0))

    def test_outlook_grading(self):
        O = pd.DataFrame({"date": ["d1", "d2", "d3", "d4"], "size": ["WIDE", "BUSIER", "NORMAL", "CALMER"], "exp_range_pts": [100, 100, 100, 100]})
        S = {"d1": (0, 300, 0, 0), "d2": (0, 200, 0, 0), "d3": (0, 100, 0, 0), "d4": (0, 50, 0, 0)}
        g = SB.outlook_score(O, S)
        self.assertEqual((g["n"], g["n_big"], g["big_avg"], g["n_other"], g["other_avg"]), (4, 2, 250.0, 2, 75.0))
        self.assertAlmostEqual(g["med_err"], 0.75)                  # misses: 200%, 100%, 0%, 50% -> median 75%
        self.assertIsNone(SB.outlook_score(O, {}))                  # no real bars -> nothing graded, no crash

    def test_london_tracker_ignores_ungraded_rows(self):
        L = pd.DataFrame({"faded": ["yes", "no", "yes", None, ""]})
        self.assertEqual(SB.london_score(L), (2, 3))

    def test_forward_section_merges_families_with_identical_trades(self):
        fw = {"n": 16, "edge": 0.19, "posterior_mean": 0.029, "posterior_sd": 0.043, "p_edge_pos": 0.75, "decision": "CONTINUE"}
        F = [{"id": "F10", "status": "forward", "forward": fw}, {"id": "F12", "status": "forward", "forward": dict(fw)},
             {"id": "F13", "status": "forward", "forward": dict(fw, n=29, edge=0.15)}, {"id": "F14", "status": "failed"}]
        lines, num = SB.forward_lines(F)
        text = "\n".join(lines)
        self.assertIn("F10/F12: 16 trades", text); self.assertIn("F13: 29 trades", text); self.assertNotIn("F14", text)
        self.assertIn("44 more trades", text); self.assertEqual(num["f10_n"], 16)

    def test_small_samples_are_labelled(self):
        self.assertIn("too few", SB._small(29)); self.assertEqual(SB._small(30), "")

    def test_full_scoreboard_builds_from_the_real_logs_and_fits_discord(self):
        lines, num = SB.build()
        text = "\n".join(lines)
        self.assertNotIn("could not be read", text)
        self.assertLess(len(text), 1990)


if __name__ == "__main__":
    unittest.main()
