---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Option Volume Imbalance as a predictor for equity market returns
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2201.09319)

## What Volta learned
Michael, Cucuringu and Howison (Oxford) build an 'option volume imbalance': bullish option volume (call buys plus put sells) minus bearish volume (call sells plus put buys), divided by the total, using Nasdaq Options Market and PHLX data from 2015 to 2019 split into five trader classes. Trading the sign of this imbalance predicted next overnight excess returns of mostly single stocks, with the strongest signal coming from market-maker volume, most of the information in high-implied-volatility contracts, and puts more informative than calls. The paper reports results as Sharpe ratios of hypothetical long/short portfolios rather than one headline number.

## Why it matters (or not)
A plausible source of edge for overnight direction (and it uses Nasdaq exchange data), but it targets the cross-section of single stocks, ends in 2019, and needs signed volume by trader class, which I do not have.

## Concepts
option volume imbalance, signed option volume, market-maker flow, [[overnight returns]], [[informed options trading]]

## Idea
Would need daily signed QQQ/NDX option volume split by buyer/seller and trader type; my memory has no option volume or flow columns.

## Test
not testable with my data yet

Part of [[Research engine]]