---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# A tug of war: Overnight versus intraday expected returns
★★★☆☆  ·  Must-read (curated)  ·  [source](https://www.sciencedirect.com/science/article/pii/S0304405X19300650)

## What Volta learned
This paper explores the relationship between overnight and intraday expected returns, suggesting a tug-of-war between the two. It implies that understanding this dynamic can provide insights into market behavior and potentially inform trading strategies.

## Why it matters (or not)
The paper's relevance is inferred from its topic, which relates to market behavior and potentially trading strategies, but without the full text, specific applicability to trading or quant models is uncertain.

## Concepts
[[overnight returns]], [[intraday returns]], market behavior

## Idea
Investigate if there's a persistent pattern in the tug-of-war between overnight and intraday expected returns that can be exploited for trading

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: power 'trend_day' (base 37%): lowest-fifth days 38% vs highest-fifth 36%, Brier skill -0.3%, better than the base rate in 6/9 unseen years
How: `-sign(k_on_return) * sign(k_on_pos-0.5)` as a predictor of 'trend_day' (next session is a trend day (body >= 60% of the range))
Touches: [[Open read (powers)]]

Part of [[Research engine]]