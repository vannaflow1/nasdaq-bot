---
tags: [paper]
relevance: 2
read: 2026-11-08
---
# Learning AI Agents, Market Makers, and Stress in Automated Markets
★★☆☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2611.01799v1)

## What Volta learned
The paper shows that markets with positive feedback (herding) and negative feedback (arbitrage) can have identical one‑day return distributions and turnover, so standard volatility or VaR metrics can’t tell them apart. However, the length of stress episodes (consecutive days with large negative moves) is much longer under herding, and the sign of the feedback can be identified from serial statistics like autocorrelation or variance‑ratio tests, requiring about (s/β)^2 log(1/δ) observations.

## Why it matters (or not)
The results are theoretical and focus on constant‑product AMMs, with no direct empirical numbers for Nasdaq or S&P futures/options.

## Concepts
feedback trading, herding vs arbitrage, stress episode length, variance‑ratio test, market‑maker liquidity fragility

## Idea
Compute the variance‑ratio statistic on the daily NQ log‑return series (l_rng) to detect the sign of feedback β; a significantly positive ratio suggests herding (positive β) while a negative ratio suggests arbitrage (negative β).

## Test
not testable with my data yet

Part of [[Research engine]]