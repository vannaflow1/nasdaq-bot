---
tags: [paper]
relevance: 4
read: 2026-11-21
---
# Prediction Inference for Hybrid Models on Realized Volatility Forecasting
★★★★☆  ·  OpenAlex  ·  [source](https://arxiv.org/pdf/2611.13212)

## What Volta learned
Adding an ARMA mean model to a GARCH‑LSTM hybrid improves point forecasts of realized volatility, and a forward‑bootstrap plus conformal‑prediction adjustment yields multi‑step prediction intervals with near‑nominal coverage even for heavy‑tailed returns.

## Why it matters (or not)
Provides a practical way to get reliable volatility forecasts and uncertainty bounds, directly useful for option pricing and risk sizing.

## Concepts
arma‑garch‑lstm hybrid, forward bootstrap, conformal prediction, prediction intervals, [[realized volatility]]

## Idea
Each day, train an ARMA‑GARCH‑LSTM hybrid on the past 250 days of realized NQ volatility (log of NQ high‑low range) and use the forward‑bootstrap algorithm to generate a 5‑day prediction interval for realized volatility; then go long a 5‑day NQ straddle when the interval width exceeds its 20‑day moving‑average, scaling position size by the interval width.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 961 sell-vol + 0 buy-vol trades on real QQQ option prices, avg -3.4 bp of QQQ per trade (placebo avg -4.2, p=0.333), halves -2.5/-4.2, win 53%, worst -730 bp, positive in 4/9 years, sell trades return -3.2% of max risk; 28% of its sell days are high-gamma days (the known edge)
How: `where(std(rv20,250) > mean(std(rv20,250),20), std(rv20,250), 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]