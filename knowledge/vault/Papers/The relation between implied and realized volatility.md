---
tags: [paper]
relevance: 4
read: 2026-10-19
---
# The relation between implied and realized volatility
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/s0304-405x(98)00034-8)

## What Volta learned
Implied volatility from S&P 100 index options can be a better predictor of future volatility than past realized volatility. It even supersedes the information from past volatility in certain cases. A regime shift around the 1987 crash affects the bias of implied volatility.

## Why it matters (or not)
The abstract relates to volatility modeling and forecasting, which is useful for traders and quants, especially those focused on options and volatility.

## Concepts
[[implied volatility]], [[realized volatility]], regime shift

## Idea
Compare the predictive power of implied volatility from S&P 100 index options versus past realized volatility for future volatility, considering potential regime shifts.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.528% (+0.5%), better in 3/9 unseen years
How: feature `iv30` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]