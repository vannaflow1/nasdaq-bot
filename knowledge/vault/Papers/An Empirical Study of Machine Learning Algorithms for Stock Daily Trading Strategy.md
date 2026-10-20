---
tags: [paper]
relevance: 3
read: 2026-10-19
---
# An Empirical Study of Machine Learning Algorithms for Stock Daily Trading Strategy
★★★☆☆  ·  OpenAlex (classic)  ·  [source](http://downloads.hindawi.com/journals/mpe/2019/7816154.pdf)

## What Volta learned
This study compares the performance of traditional machine learning algorithms and deep neural network models for daily stock trading strategies, considering transaction costs. The results show that traditional machine learning algorithms perform well, but deep neural networks perform better when transaction costs are considered.

## Why it matters (or not)
The study focuses on stock trading strategies using machine learning algorithms, but it does not specifically mention Nasdaq/S&P index futures and options.

## Concepts
[[machine learning]], [[neural networks]], transaction cost

## Idea
Can a daily trading strategy using traditional machine learning algorithms outperform a deep neural network model when transaction costs are considered?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 48.8% (always-long 56.6%), strategy -1.0 bps/day vs -0.3 for the same average exposure held constantly -> timing adds -0.7 bps/day, t=-0.22, positive in 4/9 years
How: long/short on `sign(mean(r1, 5) - mean(r1, 20))` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]