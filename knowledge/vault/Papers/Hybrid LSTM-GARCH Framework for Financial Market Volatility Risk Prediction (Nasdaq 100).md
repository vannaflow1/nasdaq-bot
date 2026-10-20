---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# Hybrid LSTM-GARCH Framework for Financial Market Volatility Risk Prediction (Nasdaq 100)
★★★☆☆  ·  uploaded by the owner  ·  [source]()

## What Volta learned
GARCH parameters fed into an LSTM beat standalone LSTM and GARCH variants on Nasdaq-100 volatility (MSE/RMSE).

## Why it matters (or not)
volatility forecasting - my range brain already does this better

## Concepts
lstm-garch, nasdaq 100

## Lesson for Volta
Keep implied vol at the core; only add GARCH-type or RNN hybrids if they beat the brain out-of-sample.

Feeds [[Self-check]]
## Idea
GARCH-family forecast as an extra range feature

## Test
TESTED ON MY DATA (Oct 2026): GARCH, GJR-GARCH and EGARCH (t-dist, refit yearly) alone have 21-27% higher out-of-sample error than my range brain, and adding them to the brain changes nothing (-0.2% to -0.7%, 2019-2025). My brain already uses implied vol, which beats GARCH. A neural blend already exists in my live tracker (+3%).

Read about itself - part of [[Self-check]]