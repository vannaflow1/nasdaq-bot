---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# The Information Content of Option Demand
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.2139/ssrn.2005763)

## What Volta learned
This paper explores the relationship between option demand and future stock price movements, suggesting that option demand contains valuable information for predicting stock returns.

## Why it matters (or not)
The paper is known to provide insights into how option market activity, particularly demand, can be used to predict stock price movements, which is highly relevant for traders and quants.

## Concepts
option demand, predictive information, [[stock returns]]

## Idea
Traders could use a measure of daily option demand as an additional feature in their predictive models for stock returns, potentially improving their strategy's performance.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 50.7% (always-long 56.6%), strategy +3.8 bps/day vs -0.1 for the same average exposure held constantly -> timing adds +3.8 bps/day, t=1.27, positive in 5/9 years
How: long/short on `pc_oi - mean(pc_oi, 20)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]