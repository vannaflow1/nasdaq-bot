---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# The Death of Fundamental Analysis? How Option Market Makers Now Dictate Spot Equity Prices
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.5281/zenodo.20572981)

## What Volta learned
This is a second listing of the same Vishal Chopra working paper on Gamma Exposure (GEX), framed as 'market makers now dictate spot prices'. It argues that dealers' mechanical delta hedging anchors prices when they are long gamma and accelerates moves when they are short gamma, and it describes trader tools such as the 'gamma flip' level, call walls and put walls as support, resistance and speed-change zones. No sample, test or numbers are given in the description. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
Duplicate of the GEX explainer already read, with strong claims but no evidence; the gamma-flip and wall levels need strike-level data I do not have.

## Concepts
gamma flip, call wall / put wall, dealer hedging flows, [[0DTE options]], reflexivity

## Idea
Short-gamma momentum: when dealer gamma rank is below 0.2 (closest proxy for being below the gamma flip), go with the 20-day QQQ trend for the next day; flat otherwise.

## Test
NO EDGE: 418 days, hit 46.2% (always-long 58.6%), avg -4.3 bps/day, t=-0.50, positive in 4/9 years
How: signal = sign(r20) when gex_rank < 0.2, else 0; uses only today's close values.

Part of [[Research engine]]