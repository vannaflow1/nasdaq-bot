---
tags: [paper]
relevance: 4
read: 2026-10-19
---
# Option Pricing when the Variance Changes Randomly: Theory, Estimation, and an Application
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://www.ideals.illinois.edu/items/29299/bitstreams/97732/data.pdf)

## What Volta learned
The paper discusses option pricing when stock variance changes randomly, requiring a riskless hedge with the stock and two options. The option price depends on the risk premium associated with random standard deviation, but can be simplified by assuming volatility risk can be diversified away.

## Why it matters (or not)
The abstract suggests a direct application to options trading, particularly for volatility-sensitive strategies.

## Concepts
[[stochastic volatility]], [[option pricing]], riskless hedge

## Idea
Investigate the relationship between stochastic volatility and option prices by comparing the model's output with actual market prices, potentially identifying mispricings.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1722 signal days, hit 49.0% (always-long 56.4%), strategy -2.0 bps/day vs +0.9 for the same average exposure held constantly -> timing adds -2.9 bps/day, t=-0.90, positive in 3/9 years
How: long/short on `z(h_rho, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]