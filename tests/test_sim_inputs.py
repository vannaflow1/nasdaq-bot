import json, math, os, unittest
import pandas as pd
from _util import ROOT
import sim_inputs as SI, sealed


class StopInput(unittest.TestCase):
    def test_newest_forecast_row_wins_and_bad_rows_are_skipped(self):
        P = pd.DataFrame({"next_date": ["2026-11-12", "2026-11-13", "2026-11-16"],
                          "feat": [json.dumps({"l_bot": -4.5}), json.dumps({"l_bot": -4.2}), "not json"]})
        session, fc = SI.latest(P)
        self.assertEqual(session, "2026-11-13"); self.assertAlmostEqual(fc, math.exp(-4.2))
        self.assertIsNone(SI.latest(pd.DataFrame({"next_date": ["2026-11-16"], "feat": ["{}"]})))

    def test_published_number_is_the_one_the_forward_test_uses(self):
        p = os.path.join(ROOT, "knowledge", "sim_inputs.json")
        if not os.path.exists(p): self.skipTest("not published yet")
        s = json.load(open(p))
        self.assertAlmostEqual(float(sealed.nq_fc_frac([s["session"]], None)[0]), s["fc_frac"], places=6)
        self.assertEqual(s["stop_share_of_range"], 0.2)


if __name__ == "__main__":
    unittest.main()
