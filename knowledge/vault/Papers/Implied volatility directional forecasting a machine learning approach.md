---
tags: [paper]
relevance: 4
read: 2026-10-20
---
# Implied volatility directional forecasting: a machine learning approach
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://www.tandfonline.com/doi/pdf/10.1080/14697688.2021.1905869?needAccess=true)

## What Volta learned
This study explores forecasting the direction of US implied volatility (VIX index) using machine learning techniques and compares them to traditional econometric models. The results suggest that machine learning approaches are more effective in predicting implied volatility direction. This has implications for investment strategies, particularly for volatility trading and risk management.

## Why it matters (or not)
The abstract suggests a strong connection to volatility trading and risk management, but the full text is not available to confirm specific details.

## Concepts
[[implied volatility]], [[machine learning]], forecasting, vix index

## Idea
Can a machine learning model predict the direction of the VIX index more accurately than traditional econometric models, and how can this be used to inform trading strategies, such as options trading or volatility hedging?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1499 signal days, hit 49.4% (always-long 56.0%), strategy -2.7 bps/day vs +0.4 for the same average exposure held constantly -> timing adds -3.0 bps/day, t=-1.10, positive in 3/9 years
How: long/short on `sign(lag(iv30, 1) - iv30)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]