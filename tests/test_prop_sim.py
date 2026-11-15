import unittest
import numpy as np
from _util import ROOT
import prop_sim as PS

PLAN = "lucid_flex_50k"


class Simulator(unittest.TestCase):
    def setUp(self):
        self.P = PS.plans(True)[PLAN]

    def test_plans_have_the_fields_the_simulator_needs(self):
        for pid, P in PS.plans(True).items():
            for k in ("size", "mll", "target", "fee", "eval_max_mnq", "fund_max_tiers", "payout_days", "caps", "split", "payouts_to_live"):
                self.assertIn(k, P, f"{pid} lacks {k}")
            self.assertGreater(P["fee"], 0, pid)

    def test_strategy_that_loses_every_day_never_passes_and_costs_the_fee(self):
        n = 300; r = PS.evaluate(np.full(n, -20.0), np.full(n, -20.0), PLAN)
        self.assertEqual((r["pass_rate"], r["avg_payout_per_eval"], r["share_with_payout"]), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r["ev_per_eval"], -self.P["fee"], places=1)

    def test_flat_strategy_earns_nothing(self):
        n = 300; r = PS.evaluate(np.zeros(n), np.zeros(n), PLAN)
        self.assertEqual((r["pass_rate"], r["avg_payout_per_eval"]), (0.0, 0.0))

    def test_account_stops_when_the_max_loss_is_hit(self):
        size = lambda phase, profit, buf: 1
        big_loss = -(self.P["mll"] / PS.MNQ + 1)                          # one day worse than the whole max loss
        r = PS.run_account(np.array([big_loss, 50, 50]), np.array([big_loss, 0, 0]), 0, self.P, size)
        self.assertEqual((r["end"], r["days"], r["payouts"]), ("blown", 1, []))

    def test_steady_winner_passes_and_gets_paid_and_more_edge_is_not_worse(self):
        rng = np.random.default_rng(1); n = 600
        ev = {}
        for name, mu in (("small", 6.0), ("big", 14.0)):
            pts = rng.normal(mu, 25.0, n); worst = np.minimum(pts, -15.0)
            ev[name] = PS.evaluate(pts, worst, PLAN)
        self.assertGreater(ev["big"]["pass_rate"], 0.5)
        self.assertGreater(ev["big"]["avg_payout_per_eval"], 0)
        self.assertGreaterEqual(ev["big"]["ev_per_eval"], ev["small"]["ev_per_eval"])

    def test_payouts_are_reduced_by_the_reliability_assumption(self):
        self.assertTrue(0 < PS.PAYOUT_RELIABILITY <= 1)


if __name__ == "__main__":
    unittest.main()
