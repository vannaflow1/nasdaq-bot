---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Institutional Equity Derivatives & Market Microstructure: Analyzing the Mechanics of Option Gamma Exposure (GEX) and its Empirical Impact on Underlying Asset Volatility
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.5281/zenodo.20572275)

## What Volta learned
This working paper explains Gamma Exposure (GEX): adding up option gamma across the chain tells you roughly how many dollars of stock dealers must buy or sell for each 1% move. When dealers are net long gamma they sell rallies and buy dips, which damps volatility and can pin price near big strikes; when they are net short gamma (often after heavy put buying) they chase the move and can amplify crashes or squeezes. The abstract describes formulas and mechanisms but reports no tested data, sample or numbers. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
The mechanism is central to NQ/QQQ options, but this is an explainer with no empirical results, and Volta already uses dealer gamma rank, so it adds little new; abstract only.

## Concepts
[[dealer gamma]], dealer delta hedging, positive vs negative gamma regime, gamma squeeze, [[strike pinning]]

## Idea
Negative-gamma feedback: in the low-gamma regime (gamma rank below 0.2), let today's range surprise and recent losses count extra in the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.533% (-0.4%), better in 5/9 unseen years
How: low = 1 if gex_rank < 0.2; features low x (l_rng - l_rng20) and low x min(r20, 0), all from today's close.

Part of [[Research engine]]