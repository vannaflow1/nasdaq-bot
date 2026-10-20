---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# Deep Neural Network and Time Series Approach for Finance Systems
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://www.igi-global.com/ViewTitle.aspx?TitleId=280571&isxn=9781799867487)

## What Volta learned
This paper explores the use of machine learning algorithms, including deep neural networks, to predict the next-day trend in index prices for the Indian National Stock Exchange (NSE). The authors use historical NSE closing price data and technical indicators to train their models.

## Why it matters (or not)
The paper is somewhat relevant to traders, but it focuses on a specific market (NSE) and does not provide direct insights into Nasdaq/S&P index futures and options.

## Concepts
[[machine learning]], [[neural networks]], time series prediction

## Idea
Can a deep neural network model trained on historical price data and technical indicators (MA, MACD, RSI, etc.) outperform traditional machine learning algorithms in predicting the next-day trend in index prices?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 50.5% (always-long 56.6%), strategy -1.1 bps/day vs +1.6 for the same average exposure held constantly -> timing adds -2.7 bps/day, t=-0.83, positive in 2/9 years
How: long/short on `sign(mean(r1, 5))` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]