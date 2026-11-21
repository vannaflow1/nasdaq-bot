---
tags: [paper]
relevance: 2
read: 2026-11-21
---
# Mathematical Framework for Dynamic Downside-Minimizing Portfolio with Exotic Option Overlay
★★☆☆☆  ·  OpenAlex  ·  [source](https://www.researchsquare.com/article/rs-11613518/latest.pdf)

## What Volta learned
The paper shows how semivariance (downside risk) optimization combined with exotic options—Asian average puts, American puts via LSM, and covered calls—can dramatically boost the Sortino ratio and cut worst‑case losses in simulated portfolios, especially when diversifying across many assets and rebalancing frequently.

## Why it matters (or not)
Offers general portfolio‑construction ideas and option‑overlay concepts, but no direct, concrete strategy for Nasdaq or S&P futures trading.

## Concepts
semivariance optimization, asian average put, longstaff‑schwartz american put, covered call overlay, calendar rebalancing

## Idea
Construct a daily‑adjusted overlay that buys an arithmetic‑average Asian put on the NQ index with a strike near the 7‑day implied move (from l_impl) and sells a covered call at the same strike, rebalancing each day; evaluate if the combined position improves the Sortino ratio of a simple long‑NQ futures position using the daily Volatility‑Adjusted ROI columns.

## Test
not testable with my data yet

Part of [[Research engine]]