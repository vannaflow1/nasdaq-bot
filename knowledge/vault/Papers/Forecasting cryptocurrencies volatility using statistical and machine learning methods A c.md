---
tags: [paper]
relevance: 3
read: 2026-10-19
---
# Forecasting cryptocurrencies volatility using statistical and machine learning methods: A comparative study
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.asoc.2023.111132)

## What Volta learned
The paper compares various statistical and machine learning methods for forecasting cryptocurrency volatility, finding no single best method for all cryptocurrencies. Simple linear models like HAR and ridge regression perform as well as complex models like LSTM and RF. Linear SVR is consistently among the best models for daily forecasts.

## Why it matters (or not)
The paper focuses on cryptocurrency volatility forecasting, which may not directly apply to Nasdaq/S&P index futures and options, but the methods discussed can be relevant to volatility modeling in general.

## Concepts
[[GARCH]], [[HAR model]], [[machine learning]], [[volatility forecasting]], [[cryptocurrency]]

## Idea
Can simple linear models like HAR and ridge regression outperform complex machine learning models like LSTM and RF in forecasting volatility of a specific cryptocurrency or index, such as Nasdaq/S&P?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.531% (+0.1%), better in 7/9 unseen years
How: feature `0.5*mean(rng,5) + 0.3*mean(rng5,5) + 0.2*mean(rng20,5)` added to the brain's range model
Touches: [[Brain]]
In the [[Near-miss pool]] - re-tested together with the others monthly.

Part of [[Research engine]]