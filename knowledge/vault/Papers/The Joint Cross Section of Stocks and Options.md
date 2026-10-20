---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# The Joint Cross Section of Stocks and Options
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.3386/w19590)

## What Volta learned
An, Ang, Bali and Cakici looked at US stocks from 1996 to 2011 and found that stocks whose call implied volatility rose most over the past month went on to beat those where it fell most by about 1.09% per month (t=3.45), while stocks whose put implied volatility rose most lagged by about 0.42% per month (t=-2.03). The effect lasted up to six months and fits the idea that informed traders act in options first. In the other direction, stocks that had risen tended to see their option implied volatility climb the next month even as realized volatility fell.

## Why it matters (or not)
It is a stock-picking result (ranking thousands of single stocks against each other each month), which does not translate directly to timing one index like QQQ the next day; my index-level version of the idea showed nothing.

## Concepts
call and put implied volatility changes, cross-sectional return predictability, [[informed options trading]], decile portfolios

## Idea
Index version of the paper's put-IV signal: be short QQQ for the next day when 30d implied vol has risen over the past month and long when it has fallen.

## Test
NO EDGE: 2001 days, hit 51.6% (always-long 56.6%), avg +4.2 bps/day, t=1.28, positive in 5/9 years
How: signal = -sign(l_iv30 today minus l_iv30 21 market days ago); also tried -sign(21-day change in 25d skew): NO EDGE (t=0.51, 4/9 years), and both changes as range-forecast features: NO EDGE (0.531% -> 0.532%, better in 3/9 years).

Part of [[Research engine]]