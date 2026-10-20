---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Volatility forecast comparison using imperfect volatility proxies
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.932890)

## What Volta learned
The paper 'Volatility forecast comparison using imperfect volatility proxies' compares different methods for forecasting volatility when using imperfect proxies for volatility. It evaluates the performance of various volatility forecasting models, considering the impact of noise in volatility proxies on forecast accuracy. The study provides insights into the reliability of different approaches for estimating and predicting volatility.

## Why it matters (or not)
This is a well-known paper on volatility forecasting, which is highly relevant for traders and quants, especially those dealing with options and volatility.

## Concepts
[[volatility forecasting]], imperfect proxies, model evaluation

## Idea
Can a GARCH model with a realized volatility proxy outperform a stochastic volatility model with an implied volatility proxy in forecasting short-term volatility of Nasdaq/S&P index futures?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.587% -> 0.587% (-0.0%), better in 4/6 unseen years
How: GARCH(1,1) volatility forecast (refit yearly on past data only, years 2017-2025) added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]