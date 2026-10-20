---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Where Does the Hedging Error Go? A Greek-by-Greek Decomposition for At-the-Money 0DTE Options under Heston
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.5281/zenodo.23271888)

## What Volta learned
The authors split the hedging error of at-the-money same-day (0DTE) options into seven Greek pieces across 1,015 SPY sessions and find gamma explains about 66% of the error's variance and vega about 38%; a delta-hedged position lost 2.41 basis points per session on average (t = -8.87). Most of the error cannot be hedged away by trading faster: about 86% of SPY's one-minute error (85% for SPX) is a fixed floor, and hedging every 10 seconds on tick data still leaves 93-98% of it. QQQ and NDX showed the same ranking, with gamma the biggest source.

## Why it matters (or not)
Worked from the abstract only (no full text available); relevant for anyone selling or market-making QQQ/NDX 0DTE options because it shows the risk is gamma and volatility jumps, not hedging speed, but it gives no daily forecasting signal I can test.

## Concepts
0dte hedging error, [[dealer gamma]], vega risk, delta hedging frequency, Heston model

## Idea
Measure the intraday delta-hedging P&L of ATM QQQ 0DTE options and relate it to dealer gamma.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - needs intraday option and stock prices, as well as dealer gamma positions, which are not available in the provided data

Part of [[Research engine]]