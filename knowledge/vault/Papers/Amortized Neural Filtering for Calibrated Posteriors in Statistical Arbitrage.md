---
tags: [paper]
relevance: 3
read: 2026-11-26
---
# Amortized Neural Filtering for Calibrated Posteriors in Statistical Arbitrage
★★★☆☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.25802v2)

## What Volta learned
The paper proposes a Neural Filter Estimator that, after being trained on simulated mean‑reverting spread paths, provides a calibrated posterior (probability distribution) over the latent state of each spread instead of a single point estimate, and shows that using this posterior for position sizing reduces the over‑optimism of traditional point‑estimate forecasts by a factor of two to eight.

## Why it matters (or not)
Introduces a way to incorporate uncertainty of spread state estimates into statistical arbitrage, which could improve risk‑adjusted sizing for futures or pairs strategies.

## Concepts
amortized neural filtering, mean‑reverting spread modeling, posterior‑based position sizing, regime‑switching inference, calibration via simulation

## Idea
Train a Neural Filter Estimator on simulated mean‑reverting spreads that match the observed residuals of a pair‑trading universe (e.g., NQ/QQQ spreads), then each day compute the posterior probability that the spread will revert within the holding horizon and size the position proportionally to that probability.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2224 signal days, hit 50.5% (always-long 56.6%), strategy +4.5 bps/day vs -1.0 for the same average exposure held constantly -> timing adds +5.5 bps/day, t=1.77, positive in 6/9 years
How: long/short on `-((es_ret + nq_vs_es) - r1) * h_kappa` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]