---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# The predictive capacity of GARCH-type models in measuring the volatility of crypto and world currencies
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0245904&type=printable)

## What Volta learned
This paper compares the performance of various GARCH-type models in forecasting the volatility of six cryptocurrencies (Bitcoin, Ripple, Litecoin, Monero, Dash, and Dogecoin) and six world currencies (Euro, British Pound, Canadian Dollar, Australian Dollar, Swiss Franc, and Japanese Yen) from 2015 to 2019. The IGARCH model outperformed others for world currencies, while the best model varied for cryptocurrencies.

## Why it matters (or not)
The paper provides useful insights into volatility modeling for cryptocurrencies and world currencies, but its direct application to Nasdaq/S&P index futures and options trading is limited.

## Concepts
[[GARCH]], [[volatility]], cryptocurrencies, value at risk

## Idea
Test the IGARCH model for forecasting volatility in cryptocurrencies and world currencies, and evaluate its performance in calculating Value at Risk (VaR) at different confidence levels.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.587% -> 0.589% (-0.3%), better in 0/6 unseen years
How: GJR(1,1) volatility forecast (refit yearly on past data only, years 2017-2025) added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]