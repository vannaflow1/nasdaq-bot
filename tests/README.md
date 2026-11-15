# Volta's self-check (tests)

Plain words: these are small automatic checks that run whenever the code changes (and once a night). Each one
feeds a piece of Volta a made-up situation with a known right answer and fails loudly if the answer changes.
They do not test whether a strategy makes money - they test that the machine does what it says.

Run them all:  `python -m unittest discover -s tests -v`   (about a minute)

| File | What it protects |
|---|---|
| `test_integrity.py` | frozen files and ledgers unchanged; every registered family still matches its frozen fingerprint; the alpha budget numbers |
| `test_status_merge.py`, `test_commit_helper.py` | two jobs saving at the same time never overwrite each other; a refused upload is retried |
| `test_bias.py` | the bias band rule; while paused nothing is ever posted but every check is still logged |
| `test_watchdog.py` | the watchdog flags a missing run or a missing result, skips holidays, alerts once not every hour |
| `test_scoreboard.py` | the weekly scoreboard counts right and labels small samples |
| `test_prop_sim.py` | the prop-account simulator: a losing strategy never gets paid, a blown account stops, fees are charged |
| `test_core_math.py` | p-values, sequential-test boundaries, the F10/F13 timer agreeing with the official forward numbers, London-open clock |
| `test_prop_search.py` | result files are parked before they reach GitHub's 100 MB limit |

If a test fails after a change, the change broke something: undo it or fix it before trusting Volta's output.
