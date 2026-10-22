---
tags: [paper]
relevance: 3
read: 2026-10-22
---
# The impact of option hedging on the spot market volatility
★★★☆☆  ·  Hunt: low dealer gamma intraday volatility impact  ·  [source](https://www.sciencedirect.com/science/article/pii/S0261560622000304/pdf)

## What Volta learned
The paper models how the aggregate gamma exposure of option market makers (OMMs) feeds back into spot market volatility via their delta‑hedging trades, showing that a net short‑gamma position by OMMs raises volatility.

## Why it matters (or not)
Provides a theoretical basis for linking dealer gamma (gex_rank) to realized volatility, which is directly measurable in our data set.

## Concepts
option market maker gamma, delta‑hedge impact, linear permanent price impact, spot volatility feedback

## Idea
Test whether days with lower dealer gamma rank (more short gamma) have higher next‑day NQ realized volatility (l_rv20) or larger next‑day range (y_rng).

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.557% -> 0.557% (-0.0%), better in 3/8 unseen years
How: feature `-rank(gex_rank, 252)` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]