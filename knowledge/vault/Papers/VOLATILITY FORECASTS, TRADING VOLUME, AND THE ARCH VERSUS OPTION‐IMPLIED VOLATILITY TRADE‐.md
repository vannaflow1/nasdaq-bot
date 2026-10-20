---
tags: [paper]
relevance: 4
read: 2026-10-19
---
# VOLATILITY FORECASTS, TRADING VOLUME, AND THE ARCH VERSUS OPTION‐IMPLIED VOLATILITY TRADE‐OFF
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://www.econstor.eu/bitstream/10419/100968/1/wp2004-06.pdf)

## What Volta learned
The paper investigates the role of trading volume in predicting the relative informativeness of volatility forecasts produced by ARCH models versus option-implied volatility forecasts. It finds that when trading volume is low, ARCH models are at least as important as options for forecasting future stock market volatility, while when volume is high, option-implied volatility is more important.

## Why it matters (or not)
The paper provides useful insights for traders and quants on the relationship between trading volume and volatility forecasts, which can be applied to Nasdaq/S&P index futures and options.

## Concepts
[[GARCH]], [[option-implied volatility]], [[trading volume]]

## Idea
A testable trading idea is to use trading volume as a switching variable between ARCH and option-implied volatility forecasts. When trading volume is low, use ARCH models for volatility forecasting, and when volume is high, use option-implied volatility.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 46.4% (always-long 56.6%), strategy -3.7 bps/day vs -4.1 for the same average exposure held constantly -> timing adds +0.4 bps/day, t=0.14, positive in 6/9 years
How: long/short on `where(rank(pc_vol, 20) > 0.5, z(atm30, 20), garch)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]