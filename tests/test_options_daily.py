import unittest
import numpy as np, pandas as pd
from _util import ROOT
import options_daily as OD


def chain(day, spot, calls_oi=100, puts_oi=100):
    rows = []
    for dte, iv in ((2, 0.30), (30, 0.20), (60, 0.22)):
        exp = pd.Timestamp(day) + pd.Timedelta(days=dte)
        for k in (spot - 10, spot, spot + 10):
            rows.append({"date": day, "expiration": exp, "strike": k, "type": "call", "volume": 5, "open_interest": calls_oi,
                         "implied_volatility": iv - (0.02 if k > spot else 0), "delta": 0.25 if k > spot else 0.5, "gamma": 0.01})
            rows.append({"date": day, "expiration": exp, "strike": k, "type": "put", "volume": 7, "open_interest": puts_oi,
                         "implied_volatility": iv + (0.03 if k < spot else 0), "delta": -0.25 if k < spot else -0.5, "gamma": 0.01})
    return rows


class DailyTable(unittest.TestCase):
    def test_one_day_numbers(self):
        o = pd.DataFrame(chain("2024-01-02", 400.0, calls_oi=300, puts_oi=100))
        t = OD.build(o, pd.DataFrame({"date": ["2024-01-02"], "close": [400.0]}))
        r = t.iloc[0]
        self.assertGreater(r.gex_norm, 0)                                  # more call OI than put OI -> positive
        self.assertAlmostEqual(r.atm_iv_front, 0.30); self.assertAlmostEqual(r.atm_iv_30, 0.20)
        self.assertAlmostEqual(r.term_ratio, 1.5); self.assertAlmostEqual(r.skew25_30, 0.23 - 0.18)
        self.assertEqual((r.oi_calls, r.oi_puts, r.vol_calls, r.vol_puts), (2700, 900, 45, 63))
        self.assertTrue(np.isnan(r.gex_rank_252))                          # no year of history yet

    def test_rank_only_looks_back(self):
        days = pd.bdate_range("2023-01-02", periods=260)
        rows, und = [], []
        for i, d in enumerate(days):
            rows += chain(d.strftime("%Y-%m-%d"), 400.0, calls_oi=100 + i, puts_oi=100); und.append((d.strftime("%Y-%m-%d"), 400.0))
        t = OD.build(pd.DataFrame(rows), pd.DataFrame(und, columns=["date", "close"]))
        self.assertEqual(len(t), 260)
        self.assertTrue(t.gex_rank_252.iloc[:252].isna().all())
        self.assertEqual(t.gex_rank_252.iloc[-1], 1.0)                     # rising GEX: each day beats the 252 before it

    def test_day_without_underlying_price_is_skipped(self):
        o = pd.DataFrame(chain("2024-01-02", 400.0) + chain("2024-01-03", 401.0))
        t = OD.build(o, pd.DataFrame({"date": ["2024-01-03"], "close": [401.0]}))
        self.assertEqual(list(t.date), ["2024-01-03"])


if __name__ == "__main__":
    unittest.main()
