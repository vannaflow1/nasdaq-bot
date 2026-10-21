---
tags: [paper]
relevance: 3
read: 2026-10-21
---
# Learning volatility-adaptive forgetting via GARCH-modulated LSTM for stock price forecasting
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2610.24386v1)

## What Volta learned
The paper proposes a new LSTM variant (Gsigmoid‑LSTM) that feeds GARCH(1,1) volatility directly into the forget gate via a custom activation (Gsigmoid), letting the network forget faster in turbulent periods and retain memory in calm markets. This architectural change yields lower MSE/MAE than standard LSTM or feature‑level GARCH‑LSTM hybrids on five daily stock datasets.

## Why it matters (or not)
Provides a potentially better model for daily price/vol forecasts, but no direct trading rule.

## Concepts
garch‑modulated forget gate, gsigmoid activation, volatility‑adaptive memory, forecasting accuracy gains

## Idea
Train a Gsigmoid‑LSTM on the daily Volta columns (e.g., l_iv30, gex_rank, term, l_rng, l_rv20) plus a GARCH(1,1) volatility series derived from the same data, then use its one‑day‑ahead price forecast as a signal (e.g., go long NQ if forecasted return > 0, short if < 0).

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires training a Gsigmoid‑LSTM model on multiple daily columns and a GARCH‑modulated volatility series, which cannot be expressed with the available deterministic formulas and rolling statistics in Volta's backtest engine.

Part of [[Research engine]]