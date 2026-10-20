---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# By Force of Habit: A Consumption-Based Explanation of Aggregate Stock Market Behavior
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.3386/w4995)

## What Volta learned
Campbell and Cochrane build a model in which people judge their well-being against a slowly moving 'habit' level of consumption, so they become much more risk-averse in bad times when consumption falls close to that habit. This single feature explains why stock prices rise in booms and fall in busts, why high prices predict low returns over long horizons, and why stock market volatility is higher in downturns, and the model tracks much of the history of US stock prices using only consumption data. The repo's text file is unreadable scanned OCR, so this summary is from the abstract only.

## Why it matters (or not)
A macro asset-pricing theory about multi-year horizons; its 'volatility is higher after declines' point is already captured by Volta's range inputs, and adding recent returns did not help the next-day range forecast.

## Concepts
habit formation, time-varying risk aversion, [[equity premium]], countercyclical volatility, long-horizon return predictability

## Idea
Countercyclical volatility: add the 20-day QQQ return and its negative part (recent drawdown) to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.530% (+0.2%), better in 3/9 unseen years
How: Built from the same-day-close r20 column: r20 and min(r20, 0); no consumption data is available to build the paper's habit measure.

Part of [[Research engine]]