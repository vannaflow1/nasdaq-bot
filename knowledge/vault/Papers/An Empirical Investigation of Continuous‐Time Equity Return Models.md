---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# An Empirical Investigation of Continuous‐Time Equity Return Models
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/1540-6261.00460)

## What Volta learned
Andersen, Benzoni and Lund fitted continuous-time models to daily equity-index returns and found that a realistic model needs both stochastic (changing) volatility and sudden jumps, with jump frequency that can vary over time. Volatility shocks are strongly negatively tied to returns, so falling markets come with rising volatility (the leverage effect). These same features line up with what index option prices show, such as steep put skew, meaning the options market prices them. Worked from the abstract only (no full text in the repo), so no parameter values are given.

## Why it matters (or not)
Explains why index options carry put skew and fat tails, which is useful context for pricing QQQ options, but the extra return and jump inputs I could build added nothing to the next-day range forecast.

## Concepts
[[stochastic volatility]], poisson jumps, [[leverage effect]], [[jump-diffusion]], option-implied skew

## Idea
Leverage effect and jumps: add today's QQQ return, its negative part, and a jump flag (today's range more than twice the 20-day average) to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.532% (-0.2%), better in 5/9 unseen years
How: Today's return taken as the previous row's y_r (close-to-close return ending today, known at today's close); jump flag from l_rng minus l_rng20 above log(2).

Part of [[Research engine]]