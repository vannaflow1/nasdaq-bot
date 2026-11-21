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
queued for testing

Part of [[Research engine]]