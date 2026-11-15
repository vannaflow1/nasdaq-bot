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
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 461 sell-vol + 0 buy-vol trades on real QQQ option prices, avg -7.0 bp of QQQ per trade (placebo avg -4.3, p=0.720), halves -4.9/-9.1, win 51%, worst -730 bp, positive in 3/9 years, sell trades return -4.9% of max risk; 2% of its sell days are high-gamma days (the known edge)
How: `where((r20 < 0) and (iv30 > mean(iv30, 20)), 1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]