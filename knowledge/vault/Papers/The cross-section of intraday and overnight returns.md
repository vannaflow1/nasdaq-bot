---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# The cross-section of intraday and overnight returns
★★★☆☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.2869624)

## What Volta learned
This paper examines the cross-section of intraday and overnight returns, providing insights into how returns are distributed during different trading periods.

## Why it matters (or not)
The paper's findings can help traders better understand market behavior and potentially inform their trading strategies, especially those focused on overnight and intraday patterns.

## Concepts
[[intraday returns]], [[overnight returns]], [[cross-section]]

## Idea
Investigate whether a trading strategy based on the cross-section of intraday and overnight returns can generate alpha, particularly by exploiting differences in return distributions between these periods.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: power 'trend_day' (base 39%): lowest-fifth days 40% vs highest-fifth 36%, Brier skill -0.8%, better than the base rate in 1/6 unseen years
How: `0.6 * rank(iv30, 60) + 0.4 * rank(k_on_range, 60)` as a predictor of 'trend_day' (next session is a trend day (body >= 60% of the range))
Touches: [[Open read (powers)]]

Part of [[Research engine]]