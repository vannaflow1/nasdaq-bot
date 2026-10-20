---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# The Earnings Call Risk and Confidence Analyzer (ERCA)
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.5281/zenodo.20044961)

## What Volta learned
The authors argue that retail traders buy short-dated options before company earnings calls and lose money when implied volatility collapses after the release, even when they guess the direction right (the 'volatility trap'). They build a complex system (social-media activity model, sentiment indicator, machine-learning forecasters, quarter-Kelly sizing with a 15% drawdown stop) and report on 500 S&P 500 earnings events (2020-2026) that their sentiment-divergence score correlates with the size of the earnings surprise (Spearman 0.48). Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
About single-stock earnings and social-media sentiment, not NQ/QQQ index days; the only transferable lesson is the familiar one that buying options right before a scheduled event pays for IV that usually collapses afterwards.

## Concepts
iv crush, earnings events, sentiment velocity, fractional kelly sizing, hawkes process

## Idea
Needs per-company earnings dates, social-media and EPS-surprise data, none of which are in my memory.

## Test
not testable with my data yet

Part of [[Research engine]]