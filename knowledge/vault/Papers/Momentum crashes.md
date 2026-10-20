---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Momentum crashes
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.sciencedirect.com/science/article/pii/S0304405X16301490/pdf)

## What Volta learned
Daniel and Moskowitz show that momentum strategies (buy recent winners, short recent losers) usually pay well but occasionally suffer long, painful losing streaks called momentum crashes. These crashes are partly predictable: they happen in panic states, after the market has fallen and when volatility is high, and they coincide with sharp market rebounds that lift the beaten-down losers. A dynamic version that scales momentum down when its forecast mean is low and its variance high roughly doubled the alpha and Sharpe ratio of plain momentum. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
The paper is about cross-sectional stock momentum, not index day-trading, but its 'avoid trend-following after a selloff in high vol' rule carries over to QQQ timing; in my test it helped plain 20-day momentum yet still fell short of an edge.

## Concepts
momentum crashes, panic states, market rebounds, dynamic risk scaling, time-varying volatility

## Idea
Trade next-day QQQ in the direction of the 20-day return, but go flat in panic states (20-day return negative and 20-day realized vol in its top 30% of the past year).

## Test
NO EDGE: 1804 days, hit 54.7% (always-long 57.2%), avg +6.4 bps/day, t=2.39, positive in 7/9 years
How: Built from same-day-close r20 and l_rv20 (vol rank over trailing 252 days). For comparison, plain 20-day momentum gave t=1.48 and going long only in panic states gave t=0.33; three variants were tried, so the improvement should not be over-read.

Part of [[Research engine]]