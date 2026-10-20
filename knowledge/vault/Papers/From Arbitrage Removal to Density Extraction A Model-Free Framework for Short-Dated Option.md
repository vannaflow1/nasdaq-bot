---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# From Arbitrage Removal to Density Extraction: A Model-Free Framework for Short-Dated Options
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2605.22792)

## What Volta learned
Very short-dated options (a few hours to a week to expiry) have tiny premiums and wide bid-ask spreads, so mid prices are unreliable and quotes can even seem to allow free-money (static arbitrage) trades. The authors first strip out quotes that would allow such arbitrage at the actual bid and ask prices (ARIES), then fit the smoothest, least-assuming price distribution that stays inside every bid-ask range (SEDEx). On a synthetic Heston test the recovered distribution matched the true one to within about 0.0001 in price, and they apply it to SPXW options from 2012-2023 (five-minute quotes, snapshot 15 minutes before the close) to build short-dated volatility smiles.

## Why it matters (or not)
A careful tool for reading what 0DTE prices imply about tomorrow's distribution, which could sharpen Volta's implied-move input, but it is a pricing method rather than a trading signal and needs full strike-level option chains I do not store; the repo text ends partway through the empirical section.

## Concepts
[[risk-neutral density]], static arbitrage, bid-ask constraints, 0dte volatility smile, spxw options

## Idea
Building a risk-neutral density needs full bid-ask option chains per strike; my memory only has summary readings (straddle move, IV, skew), so the method cannot be applied.

## Test
not testable with my data yet

Part of [[Research engine]]