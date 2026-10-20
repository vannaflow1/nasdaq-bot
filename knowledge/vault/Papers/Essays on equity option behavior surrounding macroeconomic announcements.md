---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Essays on equity option behavior surrounding macroeconomic announcements
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://udspace.udel.edu/bitstreams/879677d2-246c-4088-ab76-5e3bde45ad13/download)

## What Volta learned
This dissertation studies the behavior of equity options around macroeconomic announcements. It finds that implied volatilities of S&P 500 options can predict underlying index returns on macroeconomic news days, and that delta-neutral straddles have high returns when realized volatility is higher than expected or when price jumps occur.

## Why it matters (or not)
The paper provides useful insights into the behavior of equity options around macroeconomic announcements, which can be applied to trading and risk management strategies.

## Concepts
[[implied volatility]], macroeconomic announcements, delta-neutral straddles, [[risk premium]]

## Idea
A trading strategy that takes into account the predictive power of implied volatilities of S&P 500 options for underlying index returns on macroeconomic news days, and adjusts position sizing based on the expected risk premium for variance and jump risk.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 119 signal days, hit 51.3% (always-long 53.8%), strategy +0.4 bps/day vs +0.2 for the same average exposure held constantly -> timing adds +0.2 bps/day, t=0.15, positive in 4/9 years
How: long/short on `where(event_prem > 1, sign(iv30 - mean(iv30, 252)), 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]