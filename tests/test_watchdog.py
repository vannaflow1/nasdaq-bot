import unittest
from datetime import datetime, timedelta, timezone
from _util import ROOT
import watchdog as W

UTC = timezone.utc


def fetcher(run_age_h=0.2, change_age_h=0.2, now=None, stale_runs=(), stale_paths=(), failing=()):
    """Fake GitHub: everything fresh, except the listed workflows/paths (30 days old) and failing workflows."""
    def fetch(path):
        if path.startswith("actions/workflows/"):
            wf = path.split("/")[2]
            if "status=completed" in path: return {"workflow_runs": [{"conclusion": "failure" if wf in failing else "success"}]}
            t = now - timedelta(days=30 if wf in stale_runs else 0, hours=run_age_h)
            return {"workflow_runs": [{"updated_at": t.isoformat().replace("+00:00", "Z")}]}
        p = path.split("path=")[1].split("&")[0]
        t = now - timedelta(days=30 if p in stale_paths else 0, hours=change_age_h)
        return [{"commit": {"committer": {"date": t.isoformat().replace("+00:00", "Z")}}}]
    return fetch


WED_SESSION = datetime(2026, 11, 18, 19, 0, tzinfo=UTC)          # Wednesday, middle of the US session


class Rules(unittest.TestCase):
    def test_all_fresh_means_no_alert(self):
        self.assertEqual(W.check(WED_SESSION, fetcher(now=WED_SESSION), root="/nonexistent"), {})

    def test_a_job_that_stopped_running_is_flagged(self):
        bad = W.check(WED_SESSION, fetcher(now=WED_SESSION, stale_runs=("chain-snap.yml",)), root="/nonexistent")
        self.assertEqual([k for k in bad if k.startswith("run:")], ["run:chain-snap.yml:option-chain snapshots"])

    def test_a_green_job_that_saves_nothing_is_flagged(self):
        bad = W.check(WED_SESSION, fetcher(now=WED_SESSION, stale_paths=("knowledge/prop_search",)), root="/nonexistent")
        self.assertEqual(list(bad), ["out:knowledge/prop_search"])
        self.assertIn("without saving", bad["out:knowledge/prop_search"])

    def test_weekend_does_not_expect_session_jobs(self):
        sat = datetime(2026, 11, 21, 19, 0, tzinfo=UTC)
        bad = W.check(sat, fetcher(now=sat, stale_runs=("chain-snap.yml", "bias.yml", "session.yml"),
                                   stale_paths=("knowledge/data/chains", "knowledge/bias_log.csv")), root="/nonexistent")
        self.assertEqual(bad, {})

    def test_market_holiday_skips_market_outputs_but_not_runs(self):
        thanksgiving = datetime(2026, 11, 26, 19, 0, tzinfo=UTC)
        self.assertTrue(W.is_holiday(thanksgiving))
        bad = W.check(thanksgiving, fetcher(now=thanksgiving, stale_paths=("knowledge/data/chains", "knowledge/bias_log.csv")), root="/nonexistent")
        self.assertEqual(bad, {})
        self.assertTrue(W.is_holiday(datetime(2026, 11, 27, 3, 0, tzinfo=UTC), since_h=-1.0))     # the night after counts as the holiday's session

    def test_failing_tests_are_flagged(self):
        bad = W.check(WED_SESSION, fetcher(now=WED_SESSION, failing=("tests.yml",)), root="/nonexistent")
        self.assertEqual(list(bad), ["fail:tests.yml"])

    def test_api_error_is_reported_not_swallowed(self):
        def broken(path): raise OSError("network down")
        bad = W.check(WED_SESSION, broken, root="/nonexistent")
        self.assertTrue(bad and all(k.startswith("api:") for k in bad))

    def test_every_rule_points_at_a_workflow_that_exists(self):
        import os
        for wf in {r[0] for r in W.RUNS} | {f[0] for f in W.FAILING}:
            self.assertTrue(os.path.exists(os.path.join(ROOT, ".github", "workflows", wf)), wf)
        for path in {o[0] for o in W.OUTPUTS}:
            self.assertTrue(os.path.exists(os.path.join(ROOT, path)), path)

    def test_holiday_list_covers_this_year(self):
        self.assertTrue(any(h.startswith(str(datetime.now(UTC).year)) for h in W.HOLIDAYS))


class Alerts(unittest.TestCase):
    def test_alert_once_remind_daily_announce_fix(self):
        t0 = datetime(2026, 11, 18, 10, 0, tzinfo=UTC); bad = {"x": "thing: broke"}
        new, still, fixed, st = W.decide(bad, {}, t0)
        self.assertEqual((list(new), still, fixed), (["x"], {}, []))
        new, still, fixed, st2 = W.decide(bad, st, t0 + timedelta(hours=1))                # an hour later: stay quiet
        self.assertEqual((new, still, fixed), ({}, {}, [])); self.assertEqual(W.message(new, still, fixed, st2["open"]), (None, None))
        new, still, fixed, st3 = W.decide(bad, st2, t0 + timedelta(hours=25))              # a day later: one reminder
        self.assertEqual(list(still), ["x"])
        new, still, fixed, st4 = W.decide({}, st3, t0 + timedelta(hours=26))               # fixed: say so once
        self.assertEqual(fixed, ["thing: broke"]); self.assertEqual(st4["open"], {})
        title, body = W.message(new, still, fixed, st4["open"]); self.assertIn("all clear", title); self.assertIn("thing", body)


if __name__ == "__main__":
    unittest.main()
