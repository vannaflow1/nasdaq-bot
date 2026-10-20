---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Ultra-short-term volatility surfaces
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2603.29430)

## What Volta learned
Options expiring within a week now make up about 70% of SPX option volume (2023), and their at-the-money implied volatility jumps around from one expiry to the next instead of forming a smooth curve, which classic pricing models cannot fit. Bandi, Fusari, Gazzani and Renò propose Edgeworth++, a jump model with flexible volatility plus a per-expiry shift, that prices all six shortest SPX expiries together quickly in closed form. On 247 trading days (May 2022-May 2023, sampled at 10:30, FOMC days removed) its average error was about 1.0 volatility point, against 1.9 for a two-factor Heston-jump model and 2.8 for a rough-Heston model, with roughly 37-38% of its prices inside the bid-ask spread.

## Why it matters (or not)
Shows that day-to-day differences between 0-7 day implied vols are real structure rather than noise, which matters for reading QQQ/NQ short-dated IV, but it is a pricing model needing full option surfaces, not a next-day trading signal.

## Concepts
ultra-short-term options, atm implied-volatility term structure, edgeworth++ model, [[jump-diffusion]], 0dte pricing

## Idea
The model needs the full set of 0-7 day option smiles each day; my memory has only a 7d/30d IV ratio (already in the brain), not the per-expiry term structure the paper studies.

## Test
not testable with my data yet

Part of [[Research engine]]