---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# The Price of Political Uncertainty: Theory and Evidence from the Option Market
★★★☆☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1111/jofi.12406)

## What Volta learned
Political uncertainty affects option prices, particularly for options expiring around political events like elections and global summits. These options are more expensive due to their protective value against price, variance, and tail risks. The effect is more pronounced in weaker economies and with higher political uncertainty.

## Why it matters (or not)
The abstract suggests a relationship between political uncertainty and option prices, which could be useful for traders but lacks specific trading strategies or direct application.

## Concepts
political uncertainty, [[option pricing]], event risk

## Idea
Investigate if options with expirations around political events (e.g., elections) have higher implied volatility and if this effect is more significant during periods of economic weakness or high political uncertainty.

## Test
NOT TESTABLE (fewer than 100 signal days)
How: long/flat on `where(gap_days < 7 and event_prem > 1.2, 1, 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]