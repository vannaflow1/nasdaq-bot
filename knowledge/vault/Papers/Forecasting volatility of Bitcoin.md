---
tags: [paper]
relevance: 3
read: 2026-10-19
---
# Forecasting volatility of Bitcoin
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://www.sciencedirect.com/science/article/pii/S0275531921001616/pdf)

## What Volta learned
The study compares GARCH and HAR models for forecasting Bitcoin volatility, finding that EGARCH and APARCH perform best among GARCH models, and HAR models based on realized variance outperform GARCH models, especially for short-term forecasts.

## Why it matters (or not)
The study focuses on Bitcoin volatility forecasting using GARCH and HAR models, which may have limited direct application to Nasdaq/S&P index futures and options but provides useful knowledge on volatility modeling.

## Concepts
[[GARCH]], [[HAR model]], [[volatility forecasting]], bitcoin

## Idea
Investigate the performance of EGARCH and APARCH models for forecasting volatility in Nasdaq/S&P index futures.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.587% -> 0.587% (+0.0%), better in 3/6 unseen years
How: EGARCH(1,1) volatility forecast (refit yearly on past data only, years 2017-2025) added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]