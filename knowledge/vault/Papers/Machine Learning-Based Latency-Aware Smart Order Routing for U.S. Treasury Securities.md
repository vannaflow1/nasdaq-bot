---
tags: [paper]
relevance: 0
read: 2026-10-18
---
# Machine Learning-Based Latency-Aware Smart Order Routing for U.S. Treasury Securities
☆☆☆☆☆  ·  OpenAlex  ·  [source](https://journal.esrgroups.org/jes/article/download/9815/6353)

## What Volta learned
The authors built a machine-learning order router for US Treasuries that tries to account for quotes going stale while an order travels to a venue, and tested it on a simulated order book calibrated to FRED yield volatility. Although the classifier scored 80.1% accuracy, the router beat a simple best-price router on only 2.2% of test rounds and was actually slightly more expensive (6.561 vs 6.548 basis points, t = -3.86). The honest lesson: a high-accuracy model can still make worse decisions when it is confidently wrong on the cases that matter.

## Why it matters (or not)
Treasury execution on simulated data has nothing to do with NQ/QQQ options or day-trading forecasts; the only takeaway is the general warning that accuracy is not the same as profit.

## Concepts
smart order routing, latency, stale quotes, precision vs recall, simulated order book

## Idea
Latency-aware routing for Treasury orders.

## Test
not testable with my data yet

Part of [[Research engine]]