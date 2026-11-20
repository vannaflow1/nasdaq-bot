---
tags: [paper]
relevance: 3
read: 2026-11-20
---
# The Limits of Machine Learning in Daily Return Forecasting: Evidence from Volatility Regimes, Tail Risk, and Multi-Asset Markets
★★★☆☆  ·  OpenAlex  ·  [source](https://etamaths.com/index.php/ijaa/article/download/5493/1963)

## What Volta learned
The paper finds that daily return predictability is dominated by a simple linear momentum signal—the 5‑day rolling mean return—while a sophisticated ML model (XGBoost) offers no statistical edge over plain linear regression.

## Why it matters (or not)
Shows traders that a simple momentum feature outperforms complex ML for daily direction forecasts, useful for short‑term strategies.

## Concepts
5‑day rolling mean, linear momentum, daily return forecasting, egarch volatility, [[tail risk]]

## Idea
Enter a long (short) position in the S&P 500 (or QQQ) when the 5‑day rolling average of past daily log returns is positive (negative); exit or reverse the position the next day.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2248 signal days, hit 50.4% (always-long 56.5%), strategy -0.2 bps/day vs +1.4 for the same average exposure held constantly -> timing adds -1.6 bps/day, t=-0.48, positive in 2/10 years
How: long/short on `mean(log(1 + r1), 5)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]