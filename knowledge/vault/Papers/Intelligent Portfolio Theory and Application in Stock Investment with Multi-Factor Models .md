---
tags: [paper]
relevance: 2
read: 2026-10-22
---
# Intelligent Portfolio Theory and Application in Stock Investment with Multi-Factor Models and Trend Following Trading Strategies
★★☆☆☆  ·  Hunt: trailing stop versus fixed profit target return variance tre  ·  [source](https://www.sciencedirect.com/science/article/pii/S1877050921009285/pdf)

## What Volta learned
The authors combine multi‑factor stock‑selection models with simple trend‑following exits (high‑low channel breakout or PSR) to build an "Intelligent Portfolio" that trades a few stocks rather than holds them, reporting good returns and drawdowns on Chinese A‑shares.

## Why it matters (or not)
The work is about equity selection in China and does not address futures, options, or volatility, but the factor‑plus‑trend idea could be adapted to US index instruments.

## Concepts
multi‑factor stock ranking, trend‑following breakout, parabolic sar, sector‑focused factor model, rule‑based portfolio construction

## Idea
Create a daily screen for QQQ constituents using a lightweight multi‑factor score (e.g., value, momentum, earnings growth) and, for the top‑ranked 5 stocks, enter a long position when price breaks above its prior 10‑day high (high‑low channel) and exit on a parabolic SAR reversal; evaluate performance on the Volta daily columns (e.g., r20, y_r).

## Test
not testable with my data yet

Part of [[Research engine]]