---
tags: [paper]
relevance: 2
read: 2026-10-25
---
# Study on the Validity of Volatility Trading
★★☆☆☆  ·  Hunt: daily range forecast position sizing volatility trading  ·  [source](https://doi.org/10.3390/fintech5010026)

## What Volta learned
The paper finds that about two‑thirds of US stocks show statistically significant mean‑reversion in volatility, and that the 30‑day average implied volatility is the most reliable predictor among several metrics, while range‑based estimators and simple delta‑neutral strategy backtests do not consistently generate profit.

## Why it matters (or not)
The abstract only provides generic findings; it does not give concrete numbers or methods directly applicable to Nasdaq futures/options trading.

## Concepts
volatility mean reversion, [[implied volatility forecasting]], [[GARCH]], delta‑neutral option strategies, [[backtesting]]

## Idea
Use the 30‑day ATM implied volatility (l_iv30) as a predictor of next‑day NQ range (y_rng); go long gamma (buy short‑dated straddles) when l_iv30 is low relative to its recent average and short gamma when l_iv30 is high.

## Test
not testable with my data yet

Part of [[Research engine]]