---
tags: [paper, curated]
relevance: 2
read: 2026-10-21
---
# DRAWDOWN MEASURE IN PORTFOLIO OPTIMIZATION
★★☆☆☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.544742)

## What Volta learned
The paper introduces Conditional Drawdown (CDD), a one‑parameter family of risk measures that generalise maximal and average drawdown, similar to how CVaR generalises VaR, and shows how to optimise portfolios using CDD.

## Why it matters (or not)
Drawdown‑based risk metrics are relevant to risk management, but the paper offers no direct trading signal or model for futures/options pricing.

## Concepts
conditional drawdown, drawdown distribution, portfolio optimisation, risk measure, cvar analogy

## Idea
Create portfolios of NQ futures and options that minimise the CDD at a chosen tolerance (e.g., Alpha = 0.9) using historical multi‑scenario drawdown paths derived from daily NQ returns, then compare their realized drawdowns to portfolios optimised with standard CVaR constraints.

## Test
not testable with my data yet

Part of [[Research engine]]