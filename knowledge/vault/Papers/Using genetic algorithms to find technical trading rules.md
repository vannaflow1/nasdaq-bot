---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Using genetic algorithms to find technical trading rules
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/s0304-405x(98)00052-x)

## What Volta learned
The authors let a genetic algorithm evolve technical trading rules on daily S&P 500 prices from 1928 to 1995. After transaction costs the rules did not beat simple buy-and-hold out of sample. What the rules did learn was to be in the market when daily returns were positive and volatility low, and out otherwise, and that pattern is mostly explained by small day-to-day return autocorrelation. I worked from the abstract only because no full text was available.

## Why it matters (or not)
A useful warning that machine-searched chart rules rarely survive costs on an index, which applies to any QQQ day-trading signal, but it offers no options insight and I only had the abstract.

## Concepts
[[genetic algorithm]], [[technical trading rules]], data snooping, serial correlation, [[transaction costs]]

## Idea
Mimic what the evolved rules learned: hold QQQ long the next day only when today's return was positive and 20-day realized vol is below its past-year median, flat otherwise.

## Test
NO EDGE: 645 days, hit 56.0% (always-long 56.0%), avg +4.2 bps/day, t=1.07, positive in 5/9 years
How: Today's return = previous row's y_r; vol filter = l_rv20 below its trailing 252-day median (min 126 days); a plain follow-today's-sign rule also failed (t=-1.70), so there is no usable next-day autocorrelation in QQQ since 2017.

Part of [[Research engine]]