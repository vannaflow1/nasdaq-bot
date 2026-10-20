---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Overcoming Execution Drag in Volatility Harvesting: Hysteresis and Partial PCA Orthogonalization
★★☆☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.5281/zenodo.23435585)

## What Volta learned
A self-published (not peer-reviewed) Nifty50 study shows that a volatility-risk-premium strategy that looked good on paper (17.85% gross, Sharpe 1.84) turned into an 18.5% net loss once the cost of constantly re-hedging delta and slippage were counted. Only re-hedging less often (a 'deadband' that ignores small delta changes) and stripping out the index's main market factor brought it back to a claimed 11.44% net, Sharpe 2.03. The takeaway for a retail trader: hedging and trading costs can wipe out an options edge entirely, so trade less often and count costs first.

## Why it matters (or not)
The cost lesson applies to anyone hedging QQQ/NQ options, but the strategy is Nifty dispersion/stat-arb, data period and cost assumptions are not stated, and it is an unreviewed preprint.

## Concepts
[[volatility risk premium]], delta-hedging costs, hysteresis deadband, pca factor neutralisation, dispersion trading

## Idea
Add the volatility risk premium spread (30d implied vol minus 20d realized vol, in logs) as a feature for the next-day NQ range forecast.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.532% (-0.1%), better in 5/9 unseen years
How: feature `log(iv30 / rv20)` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]