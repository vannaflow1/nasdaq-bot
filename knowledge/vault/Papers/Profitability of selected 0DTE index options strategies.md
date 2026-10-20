---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Profitability of selected 0DTE index options strategies
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.2139/ssrn.7162898)

## What Volta learned
This study back-tested two versions of a same-day (0DTE) Iron Condor on SPX options, using one-minute index and option prices over 12 months, and reports that both versions were profitable. The authors link this to 0DTE implied volatility being priced higher than the volatility that actually followed, so option sellers collected a premium. Only the abstract was available, so the size of the profits, costs and drawdowns is not known.

## Why it matters (or not)
The topic (selling 0DTE index premium) is directly relevant to QQQ/NQ options, but I worked from the abstract only (no full text): one year of SPX data with no numbers given is too thin to trust, and it says nothing about tail losses.

## Concepts
[[0DTE options]], iron condor, implied vs realized volatility, [[volatility risk premium]], spx

## Idea
Selling a same-day iron condor pays when the realized move stays inside the options-priced move; my memory has only daily close-to-close returns and daily ranges, not intraday option prices or the condor's strikes, so the strategy itself cannot be simulated with idea_lab.

## Test
not testable with my data yet

Part of [[Research engine]]