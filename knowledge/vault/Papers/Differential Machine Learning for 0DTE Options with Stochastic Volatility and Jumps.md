---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# Differential Machine Learning for 0DTE Options with Stochastic Volatility and Jumps
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2603.07600)

## What Volta learned
The author trains a neural network to price 0DTE options and their Greeks under a model with both changing volatility and sudden jumps (Bates), learning prices and Greeks together so that one fast evaluation gives price, delta and gamma. A three-stage training that separately supervises the jump part cut the jump-term error from about 0.093 to 0.014 while keeping price errors similar, and adding jump-sensitivity labels brought the estimated jump intensity much closer to the truth (0.569 vs a true 0.60, compared with 0.739 without them). Everything is on simulated data; the author says applying it to real market data is future work, and notes gamma near the money remains the hardest thing to get right for 0DTE.

## Why it matters (or not)
A fast-pricing engineering method tested only on simulated data, useful for a market maker hedging 0DTE books but not for Volta's next-day NQ/QQQ decisions.

## Concepts
differential machine learning, [[jump-diffusion]], 0dte greeks, [[delta hedging]], model calibration

## Idea
The paper offers a pricing/hedging technique, not a market signal, and it needs option-chain data and simulated paths rather than daily readings.

## Test
not testable with my data yet

Part of [[Research engine]]