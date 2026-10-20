---
tags: [paper]
relevance: 4
read: 2026-10-19
---
# The Pricing of Tail Risk and the Equity Premium: Evidence From International Option Markets
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://pure.au.dk/ws/files/120299496/rp18_02.pdf)

## What Volta learned
The paper explores the pricing of tail risk in index options across international equity markets, finding that the tail risk premium is a potent predictor of future equity returns, while option-implied volatility only forecasts future return variation. The compensation for negative jump risk is the primary driver of the equity premium, whereas the reward for pure diffusive variance risk is unrelated to future equity returns.

## Why it matters (or not)
The paper provides useful insights into the relationship between tail risk, volatility, and equity returns, which can be applied to trading and risk management strategies.

## Concepts
[[tail risk]], [[equity premium]], [[volatility risk premium]], [[option-implied volatility]]

## Idea
Investigate the predictive power of the tail risk premium for future equity returns in a specific market, such as the S&P 500, and explore its relationship with option-implied volatility and variance risk premium.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1974 signal days, hit 49.7% (always-long 55.9%), strategy +0.3 bps/day vs -1.3 for the same average exposure held constantly -> timing adds +1.6 bps/day, t=0.53, positive in 4/9 years
How: long/short on `z(put10_wing, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]