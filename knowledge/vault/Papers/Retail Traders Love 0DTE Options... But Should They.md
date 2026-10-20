---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Retail Traders Love 0DTE Options... But Should They?
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.4404704)

## What Volta learned
This paper discusses the growing popularity of 0DTE (zero days to expiration) options among retail traders and raises concerns about their suitability for this group of investors.

## Why it matters (or not)
The paper is likely to provide valuable insights for traders, especially those interested in options trading and risk management, given its relevance to a popular trading strategy.

## Concepts
[[0DTE options]], retail traders, options trading

## Idea
Investigate the relationship between 0DTE options trading and risk management strategies, specifically examining the impact of gamma exposure on trading performance.

## Test
NOT TESTABLE (fewer than 100 trade days)
How: `where(dte0_oi_share > 0.5, -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]