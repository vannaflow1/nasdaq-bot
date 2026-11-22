---
tags: [paper]
relevance: 2
read: 2026-11-22
---
# Information Flow and Market Risk: Transformer-Based Evidence on Sentiment and Volatility Dynamics
★★☆☆☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.39636v1)

## What Volta learned
The paper finds that adding transformer‑based news sentiment (ModernFinBERT) to strong volatility‑persistence models (like HAR) does not consistently improve out‑of‑sample forecasts for individual US stocks, and the naive persistence benchmark often wins.

## Why it matters (or not)
The study focuses on equity volatility forecasts and shows limited benefit from ML news sentiment, offering modest insight for traders interested in volatility modeling.

## Concepts
[[har volatility model]], transformer news sentiment, [[qlike loss]], walk‑forward evaluation, benchmark comparison

## Idea
Compare a simple HAR model using past realized volatility and VIX (HAR‑VIX) against a naive persistence model for next‑day NQ implied volatility, and use the one with lower QLIKE loss for daily position sizing.

## Test
not testable with my data yet

Part of [[Research engine]]