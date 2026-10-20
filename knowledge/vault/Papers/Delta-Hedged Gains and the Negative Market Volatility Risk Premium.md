---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Delta-Hedged Gains and the Negative Market Volatility Risk Premium
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/hhg002)

## What Volta learned
The study examines delta-hedged option portfolios and finds that they tend to underperform, with the underperformance being greater at times of higher volatility. This suggests a negative market volatility risk premium, which significantly affects delta-hedged gains.

## Why it matters (or not)
The abstract provides evidence of a negative market volatility risk premium using S&P 500 index options, which is relevant for traders and quants.

## Concepts
delta-hedging, [[volatility risk premium]], [[stochastic volatility]]

## Idea
Investigate the relationship between delta-hedged portfolio returns and volatility levels in Nasdaq/S&P index futures and options to identify potential trading opportunities.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 52.9% (always-long 56.6%), strategy +7.2 bps/day vs +1.2 for the same average exposure held constantly -> timing adds +6.0 bps/day, t=1.94, positive in 7/9 years
How: long/short on `z(vrp, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]