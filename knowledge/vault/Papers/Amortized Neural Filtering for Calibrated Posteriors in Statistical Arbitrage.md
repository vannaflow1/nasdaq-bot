---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Amortized Neural Filtering for Calibrated Posteriors in Statistical Arbitrage
★★★★☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.25802v1)

## What Volta learned
The paper discusses using a Neural Filter Estimator (NFE) to estimate the posterior distribution of a residual spread in statistical arbitrage, which helps in correctly accounting for uncertainty in trading decisions. The NFE is trained on simulated paths of a mean-reverting process and can return the posterior over the latent state of every spread in a cross-section in one forward pass. The method reduces the gap between forecasted and realized returns by a factor of two to eight.

## Why it matters (or not)
The paper is highly relevant to traders and quants as it discusses a method for estimating uncertainty in statistical arbitrage, which can be used to improve trading decisions and risk management.

## Concepts
neural filter estimator, statistical arbitrage, posterior distribution, uncertainty estimation

## Idea
Use a Neural Filter Estimator to estimate the posterior distribution of a residual spread and size positions based on this distribution to improve statistical arbitrage trading decisions.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - needs intraday data and/or residuals from a statistical arbitrage strategy to train a neural filter estimator

Part of [[Research engine]]