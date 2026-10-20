---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Variance Risk Premiums
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/hhn038)

## What Volta learned
The paper discusses a method to quantify the variance risk premium, which is the difference between the risk-neutral expected variance and the realized variance. It proposes using a portfolio of options to approximate the variance swap rate, and then calculates the variance risk premium as the difference between realized variance and this synthetic rate.

## Why it matters (or not)
The abstract seems directly related to volatility and options, but without the full text, it's hard to assess the direct applicability to trading strategies.

## Concepts
[[volatility risk premium]], variance swap rate, [[realized volatility]]

## Idea
Investigate the relationship between the variance risk premium and future market movements, potentially using the proposed method to create a trading strategy based on the variance risk premium.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1145 signal days, hit 58.5% (always-long 58.5%), strategy +7.0 bps/day vs +3.8 for the same average exposure held constantly -> timing adds +3.2 bps/day, t=2.09, positive in 7/9 years
How: long/flat on `rank(vrp, 252) - 0.5` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]