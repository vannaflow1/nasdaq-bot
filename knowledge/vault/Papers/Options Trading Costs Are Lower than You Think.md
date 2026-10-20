---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Options Trading Costs Are Lower than You Think
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/hhaa010)

## What Volta learned
Options trading costs are often overestimated due to failure to account for traders timing their executions. By predicting price changes and buying/selling at favorable times, traders can significantly reduce their effective spreads. This means the actual cost of trading options can be lower than conventionally estimated.

## Why it matters (or not)
The abstract suggests that understanding and accurately measuring options trading costs can impact the evaluation of trading strategies' profitability.

## Concepts
effective spreads, [[price impact]], options trading costs

## Idea
Traders can reduce their effective spreads by timing executions based on predictable price changes, potentially increasing the after-cost profitability of their options trading strategies.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 44.0% (always-long 56.6%), strategy -6.9 bps/day vs -6.8 for the same average exposure held constantly -> timing adds -0.2 bps/day, t=-0.16, positive in 6/9 years
How: long/short on `sign(impl - rng)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]