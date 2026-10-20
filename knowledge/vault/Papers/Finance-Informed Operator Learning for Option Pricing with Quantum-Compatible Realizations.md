---
tags: [paper]
relevance: 0
read: 2026-10-18
---
# Finance-Informed Operator Learning for Option Pricing with Quantum-Compatible Realizations
☆☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2609.33213)

## What Volta learned
The authors train a neural network to price European options quickly under a local-volatility model by letting it learn only a correction on top of a Black-Scholes starting price, with a layer that keeps prices within no-arbitrage bounds. On test data from the same model family it cut overall relative pricing error by nearly ten times versus plain neural-network baselines, but on real index-option quotes it stayed accurate without retraining while still not beating the plain Black-Scholes formula on the same inputs. A 'quantum-compatible' version is also described, with no speed-up claimed.

## Why it matters (or not)
Read the repo's full text; a computational pricing-method paper whose real-data test did not beat Black-Scholes, so it has no use for NQ/QQQ trading decisions.

## Concepts
neural operator, local volatility, no-arbitrage bounds, near-expiry curvature, quantum computing

## Idea
None for trading; it is a faster way to compute model prices.

## Test
not testable with my data yet

Part of [[Research engine]]