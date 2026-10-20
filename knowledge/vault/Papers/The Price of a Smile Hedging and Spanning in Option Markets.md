---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# The Price of a Smile: Hedging and Spanning in Option Markets
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://kops.uni-konstanz.de/server/api/core/bitstreams/c0166dca-3fd1-4a38-9478-f8e97a07692d/content)

## What Volta learned
Using daily S&P 500 index options from 1986 to 1995, the authors test whether options beyond the at-the-money one carry information that the index and ATM option alone cannot replicate. After the 1987 crash, out-of-the-money and in-the-money options (they look out to 4% from the money) clearly add information at any confidence level, while before the crash they were redundant (only 34% confidence). In plain terms, the shape of the smile prices a separate risk such as volatility shocks or jumps, so models that just bend the volatility curve to fit prices miss something.

## Why it matters (or not)
Useful background on why put skew is its own risk signal rather than a restatement of ATM IV, but it is a pricing-theory test on 1986-95 S&P options with no direct trading rule for NQ/QQQ.

## Concepts
volatility smile, spanning test, [[stochastic volatility]], pricing kernel, 1987 crash

## Idea
If the smile carries a risk factor beyond ATM IV, add put skew (as a z-score vs its past year) and its interaction with 30d IV to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.530% -> 0.532% (-0.3%), better in 3/9 unseen years
How: skew_z = (skew - trailing 252-day mean) / trailing 252-day std (min 126 days), plus skew_z * l_iv30; all known at that day's close.

Part of [[Research engine]]