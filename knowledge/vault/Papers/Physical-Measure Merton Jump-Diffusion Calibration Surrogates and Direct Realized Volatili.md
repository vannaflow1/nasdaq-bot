---
tags: [paper]
relevance: 3
read: 2026-11-22
---
# Physical-Measure Merton Jump-Diffusion Calibration Surrogates and Direct Realized Volatility Forecasting: An Empirical and Numerical Audit on S&P 500 ETF (SPY) Returns
★★★☆☆  ·  OpenAlex  ·  [source](https://www.researchsquare.com/article/rs-11729845/latest.pdf)

## What Volta learned
The paper shows that simple ridge or LSTM models cannot reliably replace full Merton jump‑diffusion MLE for parameter estimation, but a directly trained LSTM can modestly improve 21‑day realized volatility forecasts versus EWMA and historical volatility, especially when jumps are present (e.g., COVID‑19 crash).

## Why it matters (or not)
The study compares ML surrogates to traditional volatility forecasts for SPY, which may be adapted to Nasdaq futures.

## Concepts
merton jump‑diffusion, mle calibration, ridge regression surrogate, lstm volatility forecast, ewma baseline

## Idea
Train a hybrid LSTM on recent NQ range, 30‑day IV, and realized volatility (l_rng, l_iv30, l_rv20) to predict the next 21‑day realized volatility (y_r) and use it to size option positions.

## Test
queued for testing

Part of [[Research engine]]