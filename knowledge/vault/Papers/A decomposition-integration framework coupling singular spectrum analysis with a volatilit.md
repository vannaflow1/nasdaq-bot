---
tags: [paper]
relevance: 3
read: 2026-10-21
---
# A decomposition-integration framework coupling singular spectrum analysis with a volatility-adaptive LSTM for stock price forecasting
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2610.24384v1)

## What Volta learned
The paper builds a forecasting pipeline that first splits a price series with CEEMDAN, clusters the resulting intrinsic modes by frequency, denoises the high‑frequency part with Singular Spectrum Analysis, and then predicts each component with a new LSTM cell that contains a differentiable GARCH(1,1) layer. The GARCH output scales the LSTM forget gate, so the memory decay adapts to the current volatility. Across five major US and Chinese equity indices the full system reduces out‑of‑sample RMSE by 9‑24% versus the best competing model and by 60‑70% versus a plain LSTM.

## Why it matters (or not)
It proposes a volatility‑aware deep‑learning architecture that could inspire new features or model structures for equity index forecasting.

## Concepts
ceemdan decomposition, singular spectrum analysis, garch‑modulated lstm, volatility‑adaptive forgetting, ensemble forecasting

## Idea
Create a hybrid model for S&P 500 (or NQ) next‑day return prediction that feeds daily features (e.g., l_impl, l_rng, term, l_iv30, gex_rank) into an LSTM whose forget gate is multiplied by a GARCH(1,1) conditional variance estimated on the same input series; train end‑to‑end and compare its out‑of‑sample RMSE to a standard LSTM.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2227 signal days, hit 54.1% (always-long 56.5%), strategy +1.0 bps/day vs +4.6 for the same average exposure held constantly -> timing adds -3.6 bps/day, t=-1.09, positive in 4/10 years
How: long/short on `lag(impl,1) + lag(rng,1) - lag(iv30,1) + lag(gex_rank,1)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]