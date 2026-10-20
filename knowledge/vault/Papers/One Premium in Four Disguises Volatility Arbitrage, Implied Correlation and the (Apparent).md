---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# One Premium in Four Disguises: Volatility Arbitrage, Implied Correlation and the (Apparent) Decay of the Dispersion Premium, 2006–2026
★★★☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.5281/zenodo.23355138)

## What Volta learned
Testing 2006-2026 data, this paper finds that four popular 'volatility arbitrage' trades (implied-vs-realized, VIX calendar, dispersion, skew-gated short vol) are really the same bet: each has a 0.71-0.95 daily correlation with simply shorting VIX futures, and none earns a significant extra return after correcting for testing many variants (best t-stat 2.16, failing a Holm test at p=0.09). The Cboe SKEW index was neither a source of return nor a reliable warning sign. The only add-on that held up out of sample was sizing short-vol positions in proportion to VIX (Sharpe 0.57 to 0.79), and even that is still just the plain variance premium.

## Why it matters (or not)
Directly useful as a reality check for anyone selling QQQ/NQ premium: fancy vol-arb variants mostly repackage short vol, though the paper is an unreviewed preprint and full text could not be read (only the abstract).

## Concepts
[[volatility risk premium]], multiple-testing correction, implied correlation, skew index, vix-proportional sizing

## Idea
Following the paper's claim that SKEW is not a reliable warning: go short QQQ for the next day only when put skew is in the top 10% of its past year, and see if that beats chance.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 258 signal days, hit 44.2% (always-long 55.8%), strategy -0.7 bps/day vs -0.9 for the same average exposure held constantly -> timing adds +0.2 bps/day, t=0.16, positive in 2/9 years
How: long/short on `where(rank(skew, 252) > 0.9, -1, 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]