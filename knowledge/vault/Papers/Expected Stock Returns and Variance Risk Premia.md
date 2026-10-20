---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Expected Stock Returns and Variance Risk Premia
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1093/rfs/hhp008)

## What Volta learned
The variance risk premium, which is the difference between implied and realized volatility, can predict stock market returns. High variance risk premia are associated with high future returns, while low premia are associated with low future returns.

## Why it matters (or not)
The abstract suggests a strong relationship between variance risk premia and future stock market returns, which could be useful for traders, but the full text is not available to verify the results and trading implications.

## Concepts
[[volatility risk premium]], [[implied volatility]], [[realized volatility]], stock market returns

## Idea
Investigate whether the variance risk premium can be used to predict future stock market returns, particularly at the quarterly horizon, and compare its predictive power to other popular predictor variables.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 52.9% (always-long 56.6%), strategy +7.2 bps/day vs +1.2 for the same average exposure held constantly -> timing adds +6.0 bps/day, t=1.94, positive in 7/9 years
How: long/short on `z(vrp, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]