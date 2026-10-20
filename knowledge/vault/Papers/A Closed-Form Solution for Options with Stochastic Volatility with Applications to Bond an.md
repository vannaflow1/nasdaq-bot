---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# A Closed-Form Solution for Options with Stochastic Volatility with Applications to Bond and Currency Options
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/6.2.327)

## What Volta learned
The paper presents a closed-form solution for European call options with stochastic volatility, allowing for arbitrary correlation between volatility and spot-asset returns. It also extends the model to include stochastic interest rates and applies it to bond and currency options. The solution technique uses characteristic functions.

## Why it matters (or not)
The abstract suggests a strong relevance to options and volatility modeling, but the lack of full text prevents a detailed assessment of its direct applicability to trading strategies.

## Concepts
[[stochastic volatility]], characteristic functions, [[option pricing]]

## Idea
Investigate the impact of correlation between volatility and spot-asset returns on option prices, particularly for Nasdaq/S&P index futures and options.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.532% (-0.3%), better in 3/9 unseen years
How: feature `h_rho` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]