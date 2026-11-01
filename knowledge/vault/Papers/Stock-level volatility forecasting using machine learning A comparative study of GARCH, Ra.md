---
tags: [paper]
relevance: 3
read: 2026-11-01
---
# Stock-level volatility forecasting using machine learning: A comparative study of GARCH, Random Forest, LSTM, and GRU on US Equities
★★★☆☆  ·  OpenAlex  ·  [source](https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0354643&type=printable)

## What Volta learned
Random Forest gave the lowest forecasting error (mean RMSE 0.0892) for 5‑day realized volatility of individual US stocks, beating LSTM, GRU and classic GARCH models, and it trains about seven times faster than deep‑learning nets.

## Why it matters (or not)
Provides useful insight on which volatility model works best for stock‑level forecasts, relevant for option pricing and risk sizing.

## Concepts
realized volatility forecast, random forest, garch vs ml, model training speed, rolling 5‑day window

## Idea
Train a daily Random Forest model on the Volta memory features (e.g., l_iv30, gex_rank, term, skew, l_rng, l_rng20) to predict the next‑day 5‑day annualised realized volatility; then scale option position sizes inversely with the forecasted volatility (larger positions when forecasted vol is low, smaller when high) and backtest the P&L using QQQ and NQ options.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.557% -> 0.557% (+0.0%), better in 3/8 unseen years
How: feature `0.5*rank(iv30,252) - 0.3*rank(gex_rank,252) + 0.2*rank(term,252) + 0.2*rank(skew,252) + 0.1*rank(rng,252) + 0.1*rank(rng20,252)` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]