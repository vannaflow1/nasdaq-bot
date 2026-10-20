---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Arbitrage-Free Implied Volatility Surface Reconstruction via Additive Martingales
★★★★☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.25671v1)

## What Volta learned
The paper proposes Additive Martingale (AddMart), a framework for reconstructing a continuous implied volatility (IV) surface from sparse option quotes, ensuring static no-arbitrage conditions by construction.

## Why it matters (or not)
The paper presents a novel approach to reconstructing implied volatility surfaces, which is highly relevant to traders and quants working with options, especially those focused on market making, risk management, and volatility trading.

## Concepts
additive martingale, implied volatility surface, no-arbitrage conditions, [[risk-neutral density]]

## Idea
Using an Additive Martingale framework to reconstruct IV surfaces from sparse quotes, ensuring no-arbitrage conditions and enabling the estimation of VaR, CVaR, and crash probabilities.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - requires intraday option quotes and a method to interpolate the volatility surface, not directly feasible with the provided daily closing data

Part of [[Research engine]]