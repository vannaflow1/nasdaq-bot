---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Modeling and Forecasting Realized Volatility
★★★★☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1111/1468-0262.00418)

## What Volta learned
The paper discusses using high-frequency intraday data to model and forecast daily volatility and return distributions. It introduces the concept of 'realized volatility' constructed from intraday returns, allowing for traditional time series modeling and forecasting. A simple long-memory Gaussian vector autoregression model for logarithmic daily realized volatilities performs well in forecasting volatility.

## Why it matters (or not)
The paper is highly relevant to traders and quants as it provides a framework for modeling and forecasting volatility using high-frequency data, which can be useful for risk management and trading strategies.

## Concepts
[[realized volatility]], [[high-frequency data]], [[volatility forecasting]]

## Idea
Can a long-memory Gaussian vector autoregression model for logarithmic daily realized volatilities be used to improve volatility forecasts and subsequently inform risk management and trading decisions?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.587% -> 0.587% (-0.0%), better in 4/6 unseen years
How: GARCH(1,1) volatility forecast (refit yearly on past data only, years 2017-2025) added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]