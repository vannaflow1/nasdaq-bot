---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Time Series Momentum
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.sciencedirect.com/science/article/pii/S0304405X11002613/pdf)

## What Volta learned
Across 58 liquid futures (equity indexes, currencies, commodities, bonds), an asset's own past 1-12 month return predicts its next month: winners keep rising and losers keep falling, with some reversal over longer horizons. A diversified portfolio of these trend trades earned strong returns with little exposure to normal risk factors and did best in extreme markets. Speculators profit from it at the expense of hedgers.

## Why it matters (or not)
A well-known monthly trend effect on index futures including Nasdaq-type contracts, but it is a monthly, diversified effect; on a single index at a daily horizon it did not beat simply being long.

## Concepts
time series momentum, trend following, futures, under-reaction

## Idea
Go long QQQ the next day when its past 12-month return is positive and short when negative (the paper's 12-month lookback).

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2227 signal days, hit 56.4% (always-long 56.5%), strategy +3.4 bps/day vs +5.4 for the same average exposure held constantly -> timing adds -2.0 bps/day, t=-0.74, positive in 4/10 years
How: long/short on `csum(r1, 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]