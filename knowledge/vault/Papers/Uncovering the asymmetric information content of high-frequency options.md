---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Uncovering the asymmetric information content of high-frequency options
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.jbankfin.2026.107720)

## What Volta learned
The authors split the high-frequency moves of option prices into up-moves and down-moves (semivariances) and signed jumps, using SPY options and 15 single stocks. The downside moves of out-of-the-money calls and the upside moves of OTM puts help predict future volatility, the variance risk premium and next-month excess returns, beyond plain total option volatility. A volatility-timing strategy built on these measures gained up to 206 basis points a year out of sample for a risk-averse investor.

## Why it matters (or not)
Index-ETF options and volatility prediction are on topic, but the signals need intraday option price paths we do not store, and the payoff is a monthly volatility-timing gain, not a day-trading edge.

## Concepts
realized semivariance, signed jumps, otm option returns, [[volatility timing]], [[volatility risk premium]]

## Idea
Build OTM call/put realized semivariances from intraday QQQ option prices and add them to the range forecast.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires intraday OTM call and put option prices to compute realized semivariances, which are not available in the provided dataset (only end‑of‑day surface metrics are present).

Part of [[Research engine]]