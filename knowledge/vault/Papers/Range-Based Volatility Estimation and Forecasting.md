---
tags: [paper]
relevance: 4
read: 2026-10-25
---
# Range-Based Volatility Estimation and Forecasting
★★★★☆  ·  Hunt: daily range forecast position sizing volatility trading  ·  [source](http://hdl.handle.net/10419/120419)

## What Volta learned
The thesis investigates how to improve daily high‑low range forecasts by using more efficient volatility estimators (realized variance, realized range, Parkinson, Garman‑Klass, Rogers‑Satchell) and by breaking the day into sessions (Asian, European, American) to capture distinct trading dynamics.

## Why it matters (or not)
Improved range forecasts directly inform position sizing and stop‑loss placement for volatility‑focused traders, especially in futures like NQ.

## Concepts
range‑based volatility estimators, [[realized volatility]], session‑slice modeling, forecasting daily range, position sizing

## Idea
Create a daily range forecast model that combines the Parkinson estimator (using intraday high‑low) with session‑specific realized ranges (e.g., Asian, European, American) as predictors, then use the forecasted range to size NQ futures positions via a volatility‑adjusted Kelly fraction.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.531% (+0.1%), better in 7/9 unseen years
How: feature `0.5*ewm(rng,10) + 0.3*ewm(rng5,10) + 0.2*ewm(rng20,10)` added to the brain's range model
Touches: [[Brain]]
In the [[Near-miss pool]] - re-tested together with the others monthly.

Part of [[Research engine]]