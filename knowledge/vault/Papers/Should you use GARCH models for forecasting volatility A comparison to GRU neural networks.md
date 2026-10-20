---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# Should you use GARCH models for forecasting volatility? A comparison to GRU neural networks
★★★☆☆  ·  uploaded by the owner  ·  [source]()

## What Volta learned
Walk-forward comparison of GARCH, Markov-switching GARCH, HMM and GRU: GRU forecast volatility best, HMM identified regimes best.

## Why it matters (or not)
volatility forecasting - my range brain already does this better

## Concepts
gru, regime switching, walk-forward

## Lesson for Volta
Keep implied vol at the core; only add GARCH-type or RNN hybrids if they beat the brain out-of-sample.

Feeds [[Self-check]]
## Idea
GARCH-family forecast as an extra range feature

## Test
TESTED ON MY DATA (Oct 2026): GARCH, GJR-GARCH and EGARCH (t-dist, refit yearly) alone have 21-27% higher out-of-sample error than my range brain, and adding them to the brain changes nothing (-0.2% to -0.7%, 2019-2025). My brain already uses implied vol, which beats GARCH. A neural blend already exists in my live tracker (+3%).

Read about itself - part of [[Self-check]]