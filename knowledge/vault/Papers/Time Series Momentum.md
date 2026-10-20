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
NO EDGE: 2226 days, hit 56.4% (always-long 56.6%), avg +3.4 bps/day, t=1.10, positive in 6/9 years
How: Signal = sign of the rolling 252-day sum of past daily QQQ log returns (y_r shifted one day, so only returns known at the close).

Part of [[Research engine]]