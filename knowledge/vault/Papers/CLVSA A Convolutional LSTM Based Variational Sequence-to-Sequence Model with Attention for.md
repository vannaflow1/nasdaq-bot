---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# CLVSA: A Convolutional LSTM Based Variational Sequence-to-Sequence Model with Attention for Predicting Trends of Financial Markets
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://www.ijcai.org/proceedings/2019/0514.pdf)

## What Volta learned
The paper proposes a hybrid model called CLVSA, which combines convolutional LSTM units, sequence-to-sequence architecture, and attention mechanisms to predict financial market trends. The model outperforms basic models like CNN, LSTM, and Seq2Seq with attention on backtesting results of six futures from 2010 to 2017.

## Why it matters (or not)
The paper presents a complex model for predicting financial market trends, but its direct application to trading is unclear due to the lack of specific trading strategy or risk management discussion.

## Concepts
convolutional lstm, sequence-to-sequence, attention mechanism, variational model, kullback-leibler divergence

## Idea
Can CLVSA be used to predict the next-day's trend of Nasdaq/S&P index futures by training on historical data, and how does its performance compare to traditional models?

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - requires intraday data and complex model implementation

Part of [[Research engine]]