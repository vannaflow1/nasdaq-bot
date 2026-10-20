---
tags: [paper, curated]
relevance: 5
read: 2026-10-19
---
# 0DTEs: Trading, Gamma Risk and Volatility Propagation
★★★★★  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.4692190)

## What Volta learned
This paper discusses the impact of 0-Day-To-Expiration (0DTE) options on trading, gamma risk, and volatility propagation, particularly in the context of the Nasdaq and S&P index futures and options.

## Why it matters (or not)
The paper is highly relevant to traders and quants focusing on options and volatility, especially those trading Nasdaq/S&P index futures and options.

## Concepts
[[0DTE options]], [[dealer gamma]], volatility propagation

## Idea
Investigate the relationship between 0DTE options, gamma risk, and subsequent market volatility to develop a strategy for trading or hedging.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 0 sell-vol + 1039 buy-vol trades on real QQQ option prices, avg -6.9 bp of QQQ per trade (placebo avg -5.3, p=0.733), halves -10.9/-3.0, win 41%, worst -662 bp, positive in 2/9 years
How: `where(dte0_oi_share > 0.05, -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]