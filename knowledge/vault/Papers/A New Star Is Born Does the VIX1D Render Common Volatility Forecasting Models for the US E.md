---
tags: [paper]
relevance: 4
read: 2026-10-18
---
# A New Star Is Born: Does the VIX1D Render Common Volatility Forecasting Models for the US Equity Market Obsolete?
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/fut.70023)

## What Volta learned
VIX1D is Cboe's index of how much the S&P 500 is expected to move over just the next day, built from the shortest-dated (largely 0DTE) options. The authors find it usually sits below the 30-day VIX but jumps around more, drifts upward during the trading day, and on average overstates the next day's actual move because it contains a risk premium. After a simple adjustment for that premium, VIX1D alone forecast next-day S&P volatility more accurately than the standard HAR forecasting models (the abstract gives no exact error figures).

## Why it matters (or not)
Worked from the abstract only (no full text available); directly relevant because a one-day options-implied move is exactly what Volta's next-day range forecast is built around, though my test of the premium adjustment added nothing on top of what the brain already uses.

## Concepts
[[vix1d]], one-day implied volatility, [[volatility risk premium]], [[HAR model]], [[0DTE options]]

## Idea
Premium-adjust the options-implied next-day move the way the paper adjusts VIX1D (add the trailing 60-day average gap between realized range and the prior day's implied move) and add it to the next-day NQ range forecast.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1257 sell-vol + 838 buy-vol trades on real QQQ option prices, avg -8.0 bp of QQQ per trade (placebo avg -4.9, p=0.917), halves -8.7/-7.2, win 47%, worst -973 bp, positive in 1/9 years, sell trades return -3.9% of max risk; 36% of its sell days are high-gamma days (the known edge)
How: `where(rng > impl + mean(rng - lag(impl, 1), 60), -1, where(rng < impl + mean(rng - lag(impl, 1), 60), 1, 0))`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]