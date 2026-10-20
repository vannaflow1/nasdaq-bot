---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# Pairs Trading: Performance of a Relative-Value Arbitrage Rule
★★★☆☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/hhj020)

## What Volta learned
Pairs trading involves matching stocks with similar historical price movements and betting on their relative value. This strategy yielded average annualized excess returns of up to 11% over 1962-2002. The profits seem to come from temporary mispricing of closely related stocks.

## Why it matters (or not)
The paper's relevance is limited to traders and quants because it focuses on a specific trading strategy (pairs trading) and its historical performance, but does not directly discuss risk management, backtesting, or market behavior in a way that's immediately applicable to Nasdaq/S&P index futures and options.

## Concepts
pairs trading, relative-value arbitrage, [[market efficiency]]

## Idea
Can a pairs trading strategy using normalized historical prices of Nasdaq/S&P 100 stocks generate excess returns after transaction costs?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 50.7% (always-long 56.6%), strategy +2.0 bps/day vs -0.9 for the same average exposure held constantly -> timing adds +2.9 bps/day, t=0.92, positive in 5/9 years
How: long/short on `z(rr25, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]