---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Empirical Asset Pricing via Machine Learning
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://academic.oup.com/rfs/article-pdf/33/5/2223/33209812/hhaa009.pdf)

## What Volta learned
This well-known study (Gu, Kelly and Xiu) compares machine-learning methods for forecasting stock returns and finds that trees and neural networks beat standard regressions, in some cases doubling the performance of the best regression-based strategies. Their edge comes from capturing nonlinear interactions between predictors, and every method agreed that the strongest signals are variations on momentum, liquidity and volatility. The abstract gives no other specific figures.

## Why it matters (or not)
Worked from the abstract only (no full text available); it is about the cross-section of monthly stock returns, not next-day index moves, so it is background on method rather than a direct NQ/QQQ signal, and simple interaction terms did not help the range forecast.

## Concepts
machine learning asset pricing, [[neural networks]], regression trees, nonlinear interactions, momentum and volatility signals

## Idea
Following the paper's point that predictor interactions matter, add interaction terms (options-priced move x gamma rank, today's range x term structure, options-priced move x event premium, 20d realized vol x 20d return) to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.532% (-0.1%), better in 5/9 unseen years
How: Products of existing same-day-close columns: l_bot*gex_rank, l_rng*term, l_bot*event_prem, l_rv20*r20.

Part of [[Research engine]]