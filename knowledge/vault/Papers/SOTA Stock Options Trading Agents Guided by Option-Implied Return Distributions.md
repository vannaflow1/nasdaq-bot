---
tags: [paper]
relevance: 4
read: 2026-10-22
---
# SOTA: Stock Options Trading Agents Guided by Option-Implied Return Distributions
★★★★☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2610.10407v1)

## What Volta learned
The paper introduces SOTA, an RL‑trained language‑model agent that picks among nine option‑strategy families (directional, vol, skew, curvature) instead of individual contracts, achieving 18.3% return and a 1.6 Sharpe over six months on large‑cap stocks and SPY. News helps in supervised training but hurts performance when kept during RL.

## Why it matters (or not)
Shows a concrete, high‑performing framework for dynamic option‑strategy choice that can inspire retail models.

## Concepts
strategy‑level option selection, reinforcement learning for options, option‑implied return distribution, news impact on rl, structured strategy families

## Idea
Using the daily implied‑return distribution metrics (e.g., term slope, skew, vega‑weighted gamma rank) to classify the market into one of the nine SOTA strategy families and then execute the corresponding deterministic resolver (e.g., long strangle when implied volatility term is high and skew <1).

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 0 sell-vol + 872 buy-vol trades on real QQQ option prices, avg -6.1 bp of QQQ per trade (placebo avg -5.5, p=0.597), halves -13.2/+1.0, win 44%, worst -973 bp, positive in 3/9 years
How: `where((term_ratio > 1 and skew < 1), 1, 0) * where(term_ratio > 1, -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]