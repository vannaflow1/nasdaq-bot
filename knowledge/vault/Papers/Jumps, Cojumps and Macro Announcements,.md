---
tags: [paper]
relevance: 3
read: 2026-10-21
---
# Jumps, Cojumps and Macro Announcements,
★★★☆☆  ·  Hunt: overnight trading range macroeconomic announcements Nasdaq i  ·  [source](https://s3.amazonaws.com/real.stlouisfed.org/wp/2007/2007-032.pdf)

## What Volta learned
The paper shows that specific U.S. macro releases—especially non‑farm payroll, Fed funds target, and GDP—significantly raise the probability of intraday jumps and simultaneous jumps (cojumps) across Nasdaq futures, bond futures and FX, with different assets reacting differently.

## Why it matters (or not)
Provides empirical links between macro surprises and jump risk, useful for timing volatility trades on Nasdaq futures.

## Concepts
intraday jumps, cojumps, macro news surprises, jump detection statistic, probit jump model

## Idea
When a non‑farm payroll or Fed funds target surprise exceeds its historical median, increase exposure to Nasdaq (NQ) options or gamma‑neutral strategies the next session, expecting a higher probability of a jump‑driven move.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 0 sell-vol + 2033 buy-vol trades on real QQQ option prices, avg -5.5 bp of QQQ per trade (placebo avg -5.4, p=0.573), halves -11.7/+0.7, win 42%, worst -973 bp, positive in 2/9 years
How: `where((k_fomc_day and k_red_surprise > 0) or (k_nfp_surprise > 0), -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]