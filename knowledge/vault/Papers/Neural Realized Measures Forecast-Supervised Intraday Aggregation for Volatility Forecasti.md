---
tags: [paper]
relevance: 3
read: 2026-11-20
---
# Neural Realized Measures: Forecast-Supervised Intraday Aggregation for Volatility Forecasting
★★★☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.1145/3858063.3858785)

## What Volta learned
The paper introduces Neural Realized Measures (NRM), which replace the fixed equal-weight aggregation of intraday volatility contributions with learned, positive, mean‑normalized weights that are optimized for forecasting. In simulations and crypto data, NRM cuts RMSE and QLIKE errors by roughly 7‑9% versus traditional realized measures.

## Why it matters (or not)
Provides a new method to improve volatility forecasts that could be adapted to Nasdaq/NQ options volatility modeling.

## Concepts
neural realized measures, forecast‑supervised weighting, intraday volatility aggregation, [[qlike loss]], har/midas models

## Idea
Train an NRM model on five‑minute NQ index futures price data to predict next‑day 30‑day ATM IV, then compare its QLIKE forecast error to a standard HAR realized variance model; if NRM beats HAR by >5% in out‑of‑sample, use its forecast to size option positions.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires training a Neural Realized Measures model on intraday 5‑minute NQ price data and computing out‑of‑sample QLIKE errors versus a HAR model, which cannot be expressed with the available daily columns and built‑in functions.

Part of [[Research engine]]