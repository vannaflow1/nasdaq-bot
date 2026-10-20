---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# The impact of Covid-19 on G7 stock markets volatility: Evidence from a ST-HAR model
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.irfa.2021.101671)

## What Volta learned
Using a smooth-transition HAR volatility model, which lets volatility behave differently once the market slides into a crisis regime, the authors find that every G7 stock market and every business sector switched into a crisis regime during Covid-19, though how hard and when differed. Health Care and Consumer Services were hit worst, Technology was hit last and least (lockdowns pushed people online), and the US and UK were the most affected countries. Markets reacted to Covid more like a financial crisis than like earlier pandemics.

## Why it matters (or not)
The finding that tech volatility was hit later and less in 2020 is a historical footnote for Nasdaq, not a trading signal, though the regime-switching volatility idea can be tested; I worked from the abstract only because no full text was available.

## Concepts
smooth-transition har, [[volatility regimes]], covid-19 crisis, sector volatility, g7 stock markets

## Idea
Smooth-transition HAR: let the next-day NQ range forecast use different weights on today's, 5-day and 20-day ranges when the market is in a high-volatility regime.

## Test
NO EDGE: range-forecast miss 0.529% -> 0.531% (-0.3%), better in 1/9 unseen years
How: Regime weight w = logistic((l_rv20 - its trailing 252-day median) / trailing 252-day std), past data only; added w and w times l_rng, l_rng5, l_rng20 as extra features.

Part of [[Research engine]]