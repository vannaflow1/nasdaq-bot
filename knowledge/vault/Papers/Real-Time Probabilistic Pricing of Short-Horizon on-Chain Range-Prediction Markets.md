---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# Real-Time Probabilistic Pricing of Short-Horizon on-Chain Range-Prediction Markets
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://rsisinternational.org/journals/ijrias/uploads/vol11-iss8-pg2102-2115-202609_pdf.pdf)

## What Volta learned
The paper designs a pricing engine (TESSERA) for crypto 'range-prediction' bets where a user wagers the price stays inside a band for a few seconds to minutes, quoting a payout about once per second from a live price feed. Its volatility estimate is a recency-weighted average with a shock mode, and its anti-exploit rules (re-price on acceptance, kill stale quotes) drive stale-quote leakage from 0.78% to zero in simulation. On simulated data it was well calibrated (0.88% error at a 4.67% house margin), but on real 1-second BTC/USD ticks it failed at first (26% error) until one volatility-floor setting was re-fitted (5.5%), and jumps remained its main weakness.

## Why it matters (or not)
About seconds-long crypto betting products, not NQ/QQQ options; the only transferable point is that recency-weighted volatility needs per-asset calibration and struggles with jumps.

## Concepts
range-prediction markets, ewma volatility, calibration error, latency arbitrage, [[jump risk]]

## Idea
Recency-weighted volatility with a shock mode: add a 10-day half-life EWMA of the daily NQ range and a flag for days whose range is more than double that average to the next-day range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.532% (-0.1%), better in 4/9 unseen years
How: ewma10 = log of EWMA(half-life 10 days) of exp(l_rng) up to today; shock = 1 if l_rng exceeds log(ewma) by log 2; both use data through today's close.

Part of [[Research engine]]