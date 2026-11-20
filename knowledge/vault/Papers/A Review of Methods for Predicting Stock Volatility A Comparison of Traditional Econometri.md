---
tags: [paper]
relevance: 3
read: 2026-11-20
---
# A Review of Methods for Predicting Stock Volatility: A Comparison of Traditional Econometric Models, Implied Volatility, and Machine Learning Methods
★★★☆☆  ·  OpenAlex  ·  [source](https://journals.zeuspress.org/index.php/FER/article/download/1605/1540)

## What Volta learned
The paper reviews three families of volatility forecasts – traditional econometric models (GARCH, HAR, Realized GARCH, CARR), implied‑volatility based methods, and machine‑learning approaches – and concludes that no single method dominates universally. Traditional models are still strong baselines, implied volatility adds value when variance risk premium and maturity are matched, and machine learning only helps in high‑dimensional settings with careful time‑series validation.

## Why it matters (or not)
The review summarizes methods relevant to daily volatility forecasting for Nasdaq/S&P futures but provides no new empirical results to change a trader’s current models.

## Concepts
garch/arch, [[realized volatility]], [[implied volatility]], machine‑learning forecasts, [[forecast evaluation]]

## Idea
Compare a simple GARCH(1,1) forecast of next‑day realized volatility (using l_rv20 or l_rng) to a forecast that adds the 7‑day implied volatility (from the options pack) as an extra regressor, and evaluate which reduces out‑of‑sample QLIKE error.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.587% -> 0.585% (+0.3%), better in 4/6 unseen years
How: feature `garch + lag(iv30, 1)` added to the brain's range model
Touches: [[Brain]]
In the [[Near-miss pool]] - re-tested together with the others monthly.

Part of [[Research engine]]