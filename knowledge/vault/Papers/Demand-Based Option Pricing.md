---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Demand-Based Option Pricing
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://academic.oup.com/rfs/article-pdf/22/10/4259/24453427/hhp005.pdf)

## What Volta learned
Because dealers cannot hedge options perfectly, heavy end-user demand for an option pushes its price up, by an amount tied to how much of its risk cannot be hedged away. Using data on actual dealer and end-user positions, the authors show end users are net long index options, especially out-of-the-money puts, which helps explain why index puts look expensive and why the volatility smirk exists. In short, skew is partly a price of demand, not only a forecast of crashes.

## Why it matters (or not)
A foundational reason why dealer positioning (the basis of GEX) and put skew matter for index options like QQQ/NDX, though it explains option prices rather than giving a next-day trading signal.

## Concepts
demand pressure, dealer positioning, unhedgeable risk, volatility smirk, expensive index puts

## Idea
Measure end-user net demand by strike in QQQ options and relate it to skew changes.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - needs intraday option order flow data to measure end-user net demand by strike

Part of [[Research engine]]