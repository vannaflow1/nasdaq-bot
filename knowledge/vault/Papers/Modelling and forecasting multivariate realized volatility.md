---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Modelling and forecasting multivariate realized volatility
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/jae.1152)

## What Volta learned
The paper discusses a methodology for modeling and forecasting multivariate realized volatility using fractionally integrated processes, which ensures positive definiteness of the forecast. This approach allows for flexible dependence patterns and has been shown to outperform other methods in terms of statistical precision and mean-variance trade-off in investment decisions.

## Why it matters (or not)
The abstract suggests a strong relevance to volatility modeling and forecasting, but the full text is not available to confirm its direct applicability to trading strategies.

## Concepts
[[realized volatility]], covariance matrices, fractionally integrated processes

## Idea
Can a model using fractionally integrated processes improve the forecasting of multivariate realized volatility, leading to better portfolio optimization and risk management?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 46.4% (always-long 56.6%), strategy -3.9 bps/day vs -1.2 for the same average exposure held constantly -> timing adds -2.6 bps/day, t=-0.80, positive in 4/9 years
How: long/short on `z(rv20, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]