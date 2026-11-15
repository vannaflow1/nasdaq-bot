---
tags: [paper]
relevance: 3
read: 2026-11-15
---
# Risk-Sensitive Reinforcement Learning for an Options Market Maker: An Empirical Study with Real S&P 500 Options
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2611.10956v1)

## What Volta learned
Training a reinforcement‑learning hedger on real S&P 500 option data gives a modest (~3%) reduction in CVaR‑95 tail loss versus plain delta hedging, with a larger (~9%) benefit in volatile, falling markets but a 7‑10% penalty in rising markets. The learned policy keeps a short net delta when the portfolio is negatively‑delta, especially after price drops.

## Why it matters (or not)
Provides a concrete, regime‑dependent hedge‑ratio tweak that could be added to existing market‑making or delta‑hedging rules.

## Concepts
distributional rl, cvar tail‑risk metric, state‑dependent hedge ratio, empirical vs. simulated training environments

## Idea
When the 20‑day QQQ return (r20) is negative and 30‑day ATM IV (l_iv30) is above its 20‑day average, reduce the hedge ratio to 0.8‑0.9 (i.e., under‑hedge) instead of full delta; otherwise stick to delta hedging.

## Test
queued for testing

Part of [[Research engine]]