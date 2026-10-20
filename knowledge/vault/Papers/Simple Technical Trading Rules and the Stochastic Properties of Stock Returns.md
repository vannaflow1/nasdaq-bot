---
tags: [paper, curated]
relevance: 3
read: 2026-10-19
---
# Simple Technical Trading Rules and the Stochastic Properties of Stock Returns
★★★☆☆  ·  Must-read (curated)  ·  [source](https://doi.org/10.1111/j.1540-6261.1992.tb04681.x)

## What Volta learned
The paper tests simple technical trading rules (moving average and trading range break) on the Dow Jones Index from 1897 to 1986 and finds strong support for these strategies, with buy signals generating higher and less volatile returns than sell signals.

## Why it matters (or not)
The paper's relevance is limited by its age and the specific index used (Dow Jones), but its findings on simple technical trading rules are still useful for traders.

## Concepts
moving average, trading range break, bootstrap techniques, [[GARCH]]

## Idea
Can a moving average crossover strategy generate higher returns than a buy-and-hold strategy in the Nasdaq/S&P index futures?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 49.2% (always-long 56.6%), strategy -3.7 bps/day vs +0.8 for the same average exposure held constantly -> timing adds -4.4 bps/day, t=-1.40, positive in 2/9 years
How: long/short on `sign(mean(r1, 50) - mean(r1, 200))` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]