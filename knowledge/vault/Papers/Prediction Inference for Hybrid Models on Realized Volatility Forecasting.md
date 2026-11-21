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
queued for testing

Part of [[Research engine]]