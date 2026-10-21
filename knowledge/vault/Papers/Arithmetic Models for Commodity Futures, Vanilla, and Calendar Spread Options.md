---
tags: [paper]
relevance: 2
read: 2026-10-21
---
# Arithmetic Models for Commodity Futures, Vanilla, and Calendar Spread Options
★★☆☆☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.28071v1)

## What Volta learned
The paper builds an arithmetic (Bachelier) multi‑factor stochastic‑volatility HJM model for commodity futures, showing it needs three volatility factors to fit the level and slope of the volatility term structure and that including calendar‑spread options in calibration greatly improves the model’s decorrelation between adjacent contracts and pricing of those spreads.

## Why it matters (or not)
Focuses on WTI oil futures rather than equity index futures, but the idea that calendar spread options reveal true contract decorrelation could be adapted to NQ spreads.

## Concepts
arithmetic futures model, multi‑factor stochastic volatility, calendar spread options, kalman filter estimation, decorrelaton of futures curve

## Idea
Use the implied decorrelation inferred from NQ calendar‑spread option prices (or synthetic spreads) to adjust the hedge ratio between near‑month and next‑month NQ futures, aiming to improve the daily P&L variance of a gamma‑neutral option book.

## Test
not testable with my data yet

Part of [[Research engine]]