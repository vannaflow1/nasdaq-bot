---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Enhancing Time-Series Momentum Strategies Using Deep Neural Networks
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://jfds.pm-research.com/content/iijjfds/1/4/19.full.pdf)

## What Volta learned
The paper introduces Deep Momentum Networks, a hybrid approach combining deep learning with time-series momentum strategies. It uses deep learning to simultaneously estimate trends and size positions, optimizing the Sharpe ratio. Backtested on 88 futures contracts, it outperformed traditional methods by over two times without transaction costs and up to 2-3 bps with costs.

## Why it matters (or not)
The paper is highly relevant as it discusses a testable trading strategy using machine learning, which can be applied to Nasdaq/S&P index futures and options.

## Concepts
[[neural networks]], [[time-series momentum]], [[sharpe ratio]]

## Idea
Can a deep learning model, trained to optimize the Sharpe ratio, outperform traditional time-series momentum strategies in trading Nasdaq/S&P index futures?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 53.1% (always-long 56.6%), strategy +4.5 bps/day vs +2.8 for the same average exposure held constantly -> timing adds +1.7 bps/day, t=0.48, positive in 4/9 years
How: long/short on `r20` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]