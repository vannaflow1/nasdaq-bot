---
tags: [paper]
relevance: 3
read: 2026-10-19
---
# The VIX Premium
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://utoronto.scholaris.ca/bitstreams/682f3c99-5d7d-4dee-b4b4-dafa83785523/download)

## What Volta learned
Ing-Haw Cheng (Review of Financial Studies, 2019) measures the 'VIX premium', the extra price VIX futures carry over the VIX level expected at expiry, and finds it predicts VIX futures returns almost one-for-one (coefficient 0.92) over 2004-2015. Puzzlingly, the premium falls or stays flat when risk rises, and a falling premium warns of higher risk ahead: a one-standard-deviation drop predicted about 3 points more S&P 500 realized volatility. Shorting VIX futures only while the premium was positive raised the Sharpe ratio from 0.57 (always short) to 0.87.

## Why it matters (or not)
Directly about pricing of volatility risk on the US index; the VIX-futures strategy is not something my data covers, but its core message (a negative or vanishing volatility premium marks risky periods) maps onto QQQ and tested well in my memory as a direction filter.

## Concepts
vix premium, [[volatility risk premium]], [[vix futures]], [[hedging demand]], risk timing

## Idea
Use the sign of the volatility premium as a risk switch: long QQQ for the next day when 30d implied vol is above 20d realized vol, short when it is below.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 54.2% (always-long 56.6%), strategy +9.6 bps/day vs +2.1 for the same average exposure held constantly -> timing adds +7.5 bps/day, t=2.44, positive in 7/9 years
How: long/short on `sign(vrp)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]