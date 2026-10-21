---
tags: [paper]
relevance: 4
read: 2026-10-21
---
# DeepAR: Probabilistic forecasting with autoregressive recurrent networks
★★★★☆  ·  OpenAlex (about itself)  ·  [source](https://www.sciencedirect.com/science/article/pii/S0169207019301888/pdf)

## What Volta learned
DeepAR trains a single autoregressive recurrent network on many related time series and outputs a full predictive distribution, not just point forecasts. It learns shared patterns while still adapting to each series via conditioning on past observations.

## Why it matters (or not)
Volta already uses ridge models and small neural nets; a global RNN that outputs distributions could improve its probabilistic range forecasts across many assets.

## Concepts
autoregressive recurrent network, probabilistic output, global model trained on many series, conditioning on past observations, minimal manual feature engineering

## Lesson for Volta
Add a lightweight autoregressive RNN module that, after each walk‑forward step, is updated on the batch of recent QQQ and Nasdaq futures series and used to generate a probabilistic forecast (e.g., mean + quantiles) for the next day's range.

Feeds [[Self-check]]

Read about itself - part of [[Self-check]]