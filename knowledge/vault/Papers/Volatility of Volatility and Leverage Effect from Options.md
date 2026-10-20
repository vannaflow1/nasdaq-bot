---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Volatility of Volatility and Leverage Effect from Options
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2305.04137)

## What Volta learned
The paper builds model-free estimators of how much volatility itself moves around ('vol of vol') and of the leverage effect (prices falling as volatility rises), using high-frequency prices of short-dated options. It extracts spot volatility from the options and corrects for the noise in option quotes. It is a statistics/methods paper: it shows how to measure these quantities precisely, not a trading result, and the abstract has no market numbers.

## Why it matters (or not)
Vol-of-vol and leverage matter for QQQ option pricing and skew, but this is an estimation method needing intraday option data; a crude daily version did not help the range forecast.

## Concepts
volatility of volatility, [[leverage effect]], spot volatility, short-dated options, [[nonparametric estimation]]

## Idea
Add a daily vol-of-vol proxy (20-day std of daily changes in log 30d IV) and a leverage proxy (60-day correlation of daily QQQ returns with IV changes) to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.534% (-0.5%), better in 3/9 unseen years
How: l_vov = log rolling-20 std of diff(l_iv30); lev = rolling-60 corr of today's return (y_r shifted one day) with diff(l_iv30); vol-of-vol alone gave +0.0% (4/9 years).

Part of [[Research engine]]