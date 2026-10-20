---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Deep hedging 0DTE options
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.jfs.2026.101535)

## What Volta learned
Using high-frequency SPX option data with real transaction costs, the authors train a reinforcement-learning agent to delta-hedge 0DTE options and find it beats standard Black-Scholes delta hedging at that horizon. The learned hedge kept working during the COVID-19 crash even though it was trained only on calm periods, and the paper also studies how it behaves around price jumps. The abstract gives no headline numbers for the size of the improvement.

## Why it matters (or not)
0DTE index options are close cousins of QQQ/NDX 0DTE and the finding that plain delta hedging is suboptimal near expiry matters for dealer-flow intuition, but it is about hedging, not forecasting, and needs intraday option data we do not have.

## Concepts
[[0DTE options]], deep hedging, [[reinforcement learning]], black-scholes delta, [[transaction costs]]

## Idea
Compare an RL hedge with Black-Scholes delta hedging for QQQ 0DTE options using intraday quotes.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - needs intraday option quotes and trades, as well as a reinforcement learning model implementation

Part of [[Research engine]]