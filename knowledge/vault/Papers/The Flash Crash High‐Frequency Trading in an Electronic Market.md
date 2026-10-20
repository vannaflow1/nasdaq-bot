---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# The Flash Crash: High‐Frequency Trading in an Electronic Market
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.17863/cam.51324)

## What Volta learned
Kirilenko, Kyle, Samadi and Tuzun used audit-trail, trade-by-trade data from the E-mini S&P 500 futures on May 6, 2010 (the Flash Crash) and the three days before. During the crash a large automated sell program was executed very quickly, and the most active non-designated intermediaries, classified as high-frequency traders, did not change their trading pattern as prices fell: they neither stepped in to absorb the selling nor clearly pulled away. Worked from the abstract only (no full text in the repo), so no further numbers are available.

## Why it matters (or not)
Useful background on how fast liquidity can vanish in index futures, but it is a single-day microstructure case study and gives Volta nothing it can test or use for daily NQ/QQQ options decisions.

## Concepts
flash crash, [[high-frequency trading]], [[e-mini futures]], intraday liquidity, selling pressure

## Idea
Detect intraday liquidity withdrawal during large automated sell programs from tick-level order flow.

## Test
not testable with my data yet

Part of [[Research engine]]