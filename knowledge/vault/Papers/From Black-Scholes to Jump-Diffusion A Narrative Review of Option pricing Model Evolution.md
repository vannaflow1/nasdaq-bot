---
tags: [paper]
relevance: 3
read: 2026-11-21
---
# From Black-Scholes to Jump-Diffusion: A Narrative Review of Option pricing Model Evolution
★★★☆☆  ·  OpenAlex  ·  [source](https://journals.zeuspress.org/index.php/conference/article/download/1505/1497)

## What Volta learned
The paper reviews how option pricing moved from Black‑Scholes to models that add stochastic volatility, jumps, and their combination, noting that richer models price short‑dated OTM options better but are harder to calibrate and hedge.

## Why it matters (or not)
Provides solid background on advanced option models useful for traders designing volatility‑skew strategies, but contains no specific empirical results.

## Concepts
black‑scholes, [[stochastic volatility]], [[jump‑diffusion]], svj model, affine jump‑diffusion

## Idea
Use the 7‑day/30‑day IV term‑structure (term column) as a proxy for jump intensity: when term > 1 (steeper short‑term IV), bias a delta‑neutral straddle trade toward buying OTM puts (expecting jump‑down risk).

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 0 sell-vol + 844 buy-vol trades on real QQQ option prices, avg -7.2 bp of QQQ per trade (placebo avg -5.3, p=0.700), halves -12.8/-1.6, win 44%, worst -973 bp, positive in 3/9 years
How: `where(term > 1, -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]