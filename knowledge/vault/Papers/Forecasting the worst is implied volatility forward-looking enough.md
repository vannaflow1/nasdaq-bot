---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Forecasting the worst: is implied volatility forward-looking enough?
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://link.springer.com/content/pdf/10.1057/s41261-025-00306-w.pdf)

## What Volta learned
The authors backtest a simple 1-day Value-at-Risk (the loss size you expect to exceed only rarely) on the S&P 500 using different volatility inputs. VaR built from the 30-day VIX underestimated risk in turbulent periods: losses broke the limit too often and the overshoots were too large. Preliminary evidence suggests the newer VIX1D, priced from 0DTE/1-day options, does a better job than VIX and the time-series alternatives. Worked from the abstract only (no full text in the repo), so exact breach counts are not available.

## Why it matters (or not)
Useful reminder that a 1-day implied move beats a 30-day IV for sizing next-day risk, which matches how Volta already prices the next-day move; preliminary evidence and abstract only.

## Concepts
value-at-risk, [[vix1d]], implied vs historical volatility, [[tail risk]], [[0DTE options]]

## Idea
Short-dated implied vol as a risk forecaster: add the raw options-priced next-day move (straddle) to the next-day NQ range forecast on top of the existing inputs.

## Test
[[TRANSLATION FAILED]] - TRANSLATION FAILED - RuntimeError: free AI daily limit reached

Part of [[Research engine]]