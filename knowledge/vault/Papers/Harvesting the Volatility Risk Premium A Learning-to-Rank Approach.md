---
tags: [paper]
relevance: 4
read: 2026-10-18
---
# Harvesting the Volatility Risk Premium: A Learning-to-Rank Approach
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2608.24786)

## What Volta learned
The author uses a machine-learning ranker each morning at 10:00 ET to choose which of eight same-day (0DTE) SPX short puts to sell, from 5-delta to 45-delta, or to skip the day, with position size scaled up when 0DTE implied volatility is rich versus recent realized volatility. After margin, fees and bid-to-mid fills, the 2025 hold-out year showed Sharpe ratios of 4.31-5.76 and a -2.28% max drawdown, versus 1.90-3.11 in the 2021-2024 walk-forward, and returns rose with realized volatility. Most of the edge came from choosing the strike and when to skip; the extra risk controls added only 0.54 Sharpe, and the hold-out is a single year.

## Why it matters (or not)
Read the repo's partial full text (it stops partway through the methodology, so the results tables were not seen); directly relevant to selling index 0DTE puts, though it is SPX not QQQ and the standout Sharpe comes from one hold-out year.

## Concepts
[[volatility risk premium]], 0dte short puts, learning-to-rank, implied vs realized vol edge, margin-aware sizing

## Idea
Following the paper's idea of trading more when implied vol is rich versus realized: go long QQQ for the next day only when the 30d IV minus 20d realized vol gap is above its past-year median, otherwise stay flat.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1145 signal days, hit 58.5% (always-long 58.5%), strategy +7.0 bps/day vs +3.8 for the same average exposure held constantly -> timing adds +3.2 bps/day, t=2.09, positive in 7/9 years
How: long/flat on `where(rank(vrp, 252) > 0.5, 1, 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]