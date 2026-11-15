# DRAFT - a trend/chop filter for the paused bias

**Status: draft for the owner. Nothing has been run. The bias stays paused whatever happens here until this passes.**
Written 15 Nov 2026 by Claude (Fable 5.2).

**Peek disclosure:** I have seen the bias rule's hit rate per year 2014-Jan 2026 (the table in the 15 Nov briefing)
and the live score (14/40). I have not computed anything that splits those results by any market-state measure.
The holdout years' *unconditional* results are therefore known; what a filter does to them is not.

## The question (plain words)

The hourly bias leans the right way in trending periods (2018: 60%, 2022: 63%) and the wrong way in choppy ones
(Jan 2026: 28%, live: 35%). If the market's recent behaviour tells us *in advance* which kind of period we are in,
the bias could be shown only when it is likely to work. If it does not, the bias stays off. Both answers are useful.

Honest expectation: "trending vs choppy" is known to persist only weakly from one week to the next.
The most likely result is "no usable filter". That is why this is written down before anyone looks.

## Data and split

- NQ 1-minute regular session, 2014 -> Jan 2026 (`knowledge/strat_bars.npz`), bias checks rebuilt with the live rule
  (hourly 09:00-14:00 Chicago, band 1.2x, 14 sessions; outcome = 14:59 close vs price at the check).
- **Design:** 2014-2021. **Holdout:** 2022-Jan 2026, looked at exactly once. Same split as the overnight and London
  studies.
- **Live:** the silent log since the pause (`knowledge/bias_log.csv`) is the third, final check.

## Candidate filters (10, fixed now)

Each is computed only from sessions *before* the day in question. "ON" = the measure is above its own median over the
previous 250 sessions (a rolling median, so no threshold is tuned and nothing looks ahead).

| # | Measure | Settings |
|---|---|---|
| 1-4 | Variance ratio of 30-minute returns (above 1 = trending) | 2 or 4 periods x last 10 or 20 sessions |
| 5-6 | Autocorrelation of 30-minute returns at lag 1 | last 10 or 20 sessions |
| 7-8 | Efficiency ratio: \|open-to-close\| / sum of \|30-minute moves\|, averaged | last 10 or 20 sessions |
| 9-10 | The bias rule's own hit rate on its last graded signal-days | last 10 or 20 signal-days |

## Step 1 - design years only

For each filter: bias hit rate on ON days minus hit rate on OFF days, 2014-2021.
Pick the one with the largest difference, **but only if** its ON hit rate is at least 55% and ON covers at least 40% of
signal checks. If no filter meets that: stop here, report it, do not touch the holdout. The bias stays paused.

## Step 2 - holdout, one look

The single chosen filter, unchanged, on 2022-Jan 2026. It passes only if both hold:
1. ON hit rate minus OFF hit rate is above zero with p < 0.05, one-sided, from a permutation test that shuffles the
   ON/OFF labels in blocks of 5 trading days (checks on the same day are not independent);
2. ON hit rate is at least 55% and the lower end of its 90% range (day-block bootstrap) is above 50%.

Ten filters are compared in step 1, but only one is taken to step 2, so the holdout needs no correction.

## Step 3 - live, with a kill rule declared now

If it passes, `/bias` comes back **only on ON days**, labelled with the filter state and both test results, and the
weekly scoreboard tracks it. If fewer than 20 of the first 40 graded ON checks are right, it is paused again without
discussion. It is never inverted.

## What this is not

- Not a prop edge and not a family. It uses no alpha slot (the bias has always been owner-facing context, separate
  from the prop-edge hunt). A filter that passes here says nothing about F10/F13; gating those would need its own
  registered family.
- Not a promise. A 55% lean on some days is a small thing.

## What I need from you

A yes or no to running exactly this. If yes: one commit freezes this file (hash recorded in the result), a script
`tools/regime_study.py` runs step 1, and step 2 runs only if step 1 says so. Results go to
`knowledge/research_out/regime_*.json` and into the weekly scoreboard.
