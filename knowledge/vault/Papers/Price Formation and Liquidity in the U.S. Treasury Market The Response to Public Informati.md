---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Price Formation and Liquidity in the U.S. Treasury Market: The Response to Public Information
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/0022-1082.00172)

## What Volta learned
Fleming and Remolona studied how US Treasury prices, volume and bid-ask spreads react to major macro announcements. In a brief first stage the price jumps almost instantly while trading volume actually drops and spreads widen sharply, showing prices can reprice to news without much trading. In a longer second stage volume surges, volatility stays elevated and spreads remain somewhat wide as traders reconcile their different readings of the news. Worked from the abstract only (no full text in the repo), so no timing or size figures are given.

## Why it matters (or not)
The two-stage reaction (instant jump, then lingering volatility) is relevant to trading NQ around CPI or jobs releases, but the paper is intraday Treasury data, and testing whether an event day lifts the following day's NQ range found nothing.

## Concepts
[[macro announcements]], [[price discovery]], bid-ask spreads, post-announcement volatility, treasury market liquidity

## Idea
Post-announcement persistence: add a flag and the size of the implied event premium for today's session to the next-day NQ range forecast, to see whether volatility lingers into the day after a scheduled event.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.531% (-0.0%), better in 5/9 unseen years
How: Built from the previous row's event_prem (the options-implied premium for today's session, known before today's close): its log and a flag for values above 1.2.

Part of [[Research engine]]