---
tags: [paper]
relevance: 2
read: 2026-11-22
---
# A Comparative Analysis of Volatility Predictions via EGARCH, Transformer and Hybrid EGARCH-Transformer Models: Changes in Forecasting Ability after Introducing Sentiment Factors
★★☆☆☆  ·  OpenAlex  ·  [source](https://aemps.ewapub.com/article/view/38470.pdf)

## What Volta learned
The paper compares three ways to forecast Bitcoin volatility – a classic EGARCH model, a deep‑learning Transformer, and a hybrid that feeds EGARCH’s one‑step‑ahead variance into a Transformer. Adding Reddit sentiment sometimes helps, sometimes hurts, and overall the quality of features matters more than model complexity.

## Why it matters (or not)
The study is about crypto volatility, not Nasdaq/S&P futures, and uses sentiment data not available in our option‑price columns.

## Concepts
[[GARCH]], [[transformer]], hybrid model, sentiment features, [[volatility forecasting]]

## Idea
Use the daily EGARCH conditional variance (computed on QQQ returns) as an additional feature for a Transformer that also ingests our existing columns (e.g., l_iv30, l_rv20, gex_rank). Compare its out‑of‑sample RMSE to a plain EGARCH‑only forecast of next‑day QQQ realized volatility.

## Test
not testable with my data yet

Part of [[Research engine]]