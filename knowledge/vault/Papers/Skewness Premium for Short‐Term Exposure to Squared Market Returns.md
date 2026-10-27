---
tags: [paper]
relevance: 4
read: 2026-10-27
---
# Skewness Premium for Short‐Term Exposure to Squared Market Returns
★★★★☆  ·  Hunt: intraday option skew predicts short term returns  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/fut.22615)

## What Volta learned
The paper isolates the premium for exposure to the square of the S&P 500 daily return using a pure options strategy, finding a negative skewness premium of about 5% per year (puts outperform calls). The effect is strong at daily horizons but fades over longer periods.

## Why it matters (or not)
Directly quantifies a short‑term skew‑based return edge that can be tested and potentially exploited with daily options data.

## Concepts
skewness premium, squared market return exposure, short‑term option skew, put–call asymmetry, daily vs multi‑month horizon

## Idea
Create a zero‑cost daily strategy that isolates exposure to the squared S&P 500 return by going long ATM puts and short an equal‑delta ATM call (or vice‑versa) weighted by gamma, then track its daily P&L and compare the annualised return to the 5% premium reported.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 873 sell-vol + 0 buy-vol trades on real QQQ option prices, avg -6.5 bp of QQQ per trade (placebo avg -4.7, p=0.760), halves -9.4/-3.6, win 51%, worst -454 bp, positive in 2/9 years, sell trades return -4.6% of max risk; 31% of its sell days are high-gamma days (the known edge)
How: `where(rank(vrp, 252) > 0.6, 1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]