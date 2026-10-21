---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# Equilibrium Effects of Intraday Order-Splitting Benchmarks
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/1803.08336)

## What Volta learned
This is a theory paper (no market data) that models big institutions slicing their orders through the day to track TWAP or VWAP benchmarks, a style the authors note makes up roughly half of institutional trading. In the model, a net buy (sell) imbalance in these sliced orders pushes prices up (down) at the open, and that price pressure then fades over the session, so prices drift against the opening push on average. Tracking these benchmarks also makes the market less liquid and more volatile than if the same investors only cared about where they ended the day.

## Why it matters (or not)
The idea that opening pressure from sliced institutional orders tends to fade during the day is a reasonable intraday intuition for NQ, but the paper is purely theoretical with only numerical illustrations, and it gives no measured effect sizes to trade on.

## Concepts
twap/vwap order splitting, intraday price pressure, [[market liquidity]], equilibrium model, institutional execution

## Idea
Would need intraday data (opening move vs. rest-of-day drift) and institutional order-flow imbalance; my memory has one row per day with next-day range and return only, so the intraday fade cannot be checked.

## Test
[[TRANSLATION FAILED]] - TRANSLATION FAILED - RuntimeError: free AI daily limit reached

Part of [[Research engine]]