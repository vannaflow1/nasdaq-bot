---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# The probability of backtest overfitting
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.2139/ssrn.2326253)

## What Volta learned
The paper discusses the issue of backtest overfitting in investment strategies and proposes a new framework, Combinatorially Symmetric Cross-Validation (CSCV), to estimate the probability of backtest overfitting (PBO). This framework aims to improve the reliability of backtests used by firms and portfolio managers.

## Why it matters (or not)
The abstract is available, but the full text is not; relevance is inferred from the abstract.

## Concepts
[[backtest overfitting]], probability of backtest overfitting, combinatorially symmetric cross-validation

## Idea
Can CSCV be used to evaluate the robustness of a trading strategy's backtest by estimating the PBO, and thereby help in selecting more reliable strategies?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 50.1% (always-long 56.6%), strategy -2.6 bps/day vs +1.1 for the same average exposure held constantly -> timing adds -3.7 bps/day, t=-1.16, positive in 2/9 years
How: long/short on `z(ewm(r1, 10), 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]