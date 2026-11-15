import json, os, sys, tempfile, unittest
from datetime import datetime, timedelta
from unittest import mock
import numpy as np, pandas as pd
from _util import ROOT
import bias


def make_bars(days, today_move):
    """Quiet history days (price 0.1% above the open all day) + a `today` that sits today_move away from its open."""
    rows = []
    for k, d in enumerate(days):
        o = 20000.0; mv = today_move if k == len(days) - 1 else 0.001
        for m in range(390):
            ts = datetime(d.year, d.month, d.day, 8, 30) + timedelta(minutes=m)
            rows.append({"ts": ts, "open": o, "close": o * (1 + mv)})
    return pd.DataFrame(rows)


DAYS = [datetime(2026, 11, 5) + timedelta(days=i) for i in range(13) if (datetime(2026, 11, 5) + timedelta(days=i)).weekday() < 5]
NOW = "2026-11-17 09:05"                                        # a Tuesday, 5 minutes after the first hourly check


class BandRule(unittest.TestCase):
    def test_sessions_grid(self):
        S = bias.sessions(make_bars(DAYS, 0.001))
        self.assertEqual(len(S), len(DAYS))
        o, closes, n = S[DAYS[0].date()]
        self.assertEqual((o, len(closes), n), (20000.0, 390, 390))

    def run_check(self, move, paused):
        d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "knowledge"))
        posts = []
        fake_q = mock.MagicMock(); fake_q.push.side_effect = lambda *a, **k: posts.append(a)
        with mock.patch.object(bias, "HERE", d), mock.patch.object(bias, "K", os.path.join(d, "knowledge")), \
             mock.patch.object(bias, "LOG", os.path.join(d, "knowledge", "bias_log.csv")), \
             mock.patch.object(bias, "PAUSED", paused), mock.patch.object(bias, "bars", lambda now: make_bars(DAYS, move)), \
             mock.patch.dict(sys.modules, {"qqq_gex_daily": fake_q}), mock.patch.object(sys, "argv", ["bias.py", "--at", NOW]):
            bias.main()
            log = pd.read_csv(os.path.join(d, "knowledge", "bias_log.csv"))
            status = json.load(open(os.path.join(d, "status.json")))["bias"]
        return log, status, posts

    def test_price_above_the_band_is_long_below_is_short_inside_is_none(self):
        for move, want in ((0.01, "LONG"), (-0.01, "SHORT"), (0.0005, "NONE")):
            log, _, _ = self.run_check(move, paused=False)
            self.assertEqual(log.bias.iloc[-1], want, move)
            self.assertAlmostEqual(log.band_pct.iloc[-1], 0.12, places=3)          # 1.2 x the 0.1% average move

    def test_running_bias_posts_once_per_change(self):
        log, status, posts = self.run_check(0.01, paused=False)
        self.assertEqual(len(posts), 1); self.assertTrue(status[1].startswith("Now:"))

    def test_paused_bias_never_posts_but_still_logs(self):
        log, status, posts = self.run_check(0.01, paused=True)
        self.assertEqual(posts, [], "a paused bias must not post to Discord")
        self.assertEqual((len(log), log.bias.iloc[-1]), (1, "LONG"))               # logged silently
        self.assertTrue(status[0].startswith("⏸️")); self.assertFalse(any(x.startswith(("Now:", "Today:")) for x in status))

    def test_the_switch_in_the_repo_is_paused(self):
        self.assertTrue(bias.PAUSED, "bias.PAUSED was switched on without a tested trend/chop filter?")


if __name__ == "__main__":
    unittest.main()
