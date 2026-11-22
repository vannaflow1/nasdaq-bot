---
tags: [paper]
relevance: 3
read: 2026-11-22
---
# Neural Network Calibration of the Heston Stochastic Volatility Model
★★★☆☆  ·  OpenAlex  ·  [source](https://aemps.ewapub.com/article/view/37802.pdf)

## What Volta learned
Neural networks can approximate either the Heston pricing map (MtP) or the inverse map from option surfaces to Heston parameters (PtM). PtM gives the fastest online inference but still needs checks for admissibility and exact repricing; MtP keeps an explicit calibration objective and transparent residuals but requires an optimizer. Neither approach fixes the fundamental weak identifiability of Heston parameters, so uncertainty monitoring and fallback to classic calibration are essential.

## Why it matters (or not)
The paper discusses speeding up Heston calibration, directly relevant to the daily Heston fit column in Volta's data set.

## Concepts
heston stochastic volatility model, parameter-to-price surrogate, price-to-parameter direct inversion, weak parameter identifiability, hybrid calibration workflow

## Idea
Train a PtM convolutional neural network on the historical daily implied‑volatility grids (7d, 30d, 60d, 90d IVs) to predict the five Heston parameters, then on each new day compare the NN output to the exact Heston fit provided (kappa, thetā, sigma, rho, v0) and measure latency and pricing error; use the NN prediction as a warm‑start for a quick optimizer and fall back to full calibration when residuals exceed a threshold.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires a neural‑network generated estimate of the Heston parameters, which is not present in Volta's dataset; only the calibrated Heston parameters are available, so the proposed comparison and latency measure cannot be expressed.

Part of [[Research engine]]