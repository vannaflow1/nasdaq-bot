---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# Empirical Performance of Alternative Option Pricing Models
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/j.1540-6261.1997.tb02749.x)

## What Volta learned
This classic study (Bakshi, Cao and Chen) builds an option model where volatility, interest rates and sudden jumps can all vary, and tests simpler versions against it on S&P 500 options. Adding changing volatility and jumps matters most for pricing options accurately and for making the implied numbers line up with actual market behavior. For hedging, though, a model with changing volatility alone worked best; the abstract gives no specific error numbers.

## Why it matters (or not)
Worked from the abstract only (no full text available); foundational pricing theory that explains why smiles exist, but it gives no direct NQ/QQQ trading or forecasting signal.

## Concepts
[[stochastic volatility]], [[jump risk]], option pricing models, hedging performance, s&p 500 options

## Idea
Compare hedging errors of stochastic-volatility vs jump models on QQQ options.

## Test
not testable with my data yet

Part of [[Research engine]]