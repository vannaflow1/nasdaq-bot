---
tags: [paper]
relevance: 4
read: 2026-10-19
---
# FOMO: FLEX Options and Market Outcomes
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2610.13044)

## What Volta learned
The paper studies the impact of FLEX options, customized exchange-traded contracts, on regular listed-option markets and underlying equities. It finds that FLEX activity is associated with increased listed-option open interest, particularly in high implied-volatility environments, and predicts execution-stressed short-straddle returns.

## Why it matters (or not)
The paper provides useful insights for traders and quants, particularly those interested in volatility trading and institutional market activity.

## Concepts
flex options, [[implied volatility]], listed-option open interest, volatility carry

## Idea
Can we develop a trading strategy that uses FLEX activity as a signal to predict increased listed-option open interest and volatility in specific underlyings?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 926 signal days, hit 56.0% (always-long 56.0%), strategy +2.5 bps/day vs +3.1 for the same average exposure held constantly -> timing adds -0.6 bps/day, t=-0.39, positive in 5/9 years
How: long/flat on `z(oi_conc5, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]