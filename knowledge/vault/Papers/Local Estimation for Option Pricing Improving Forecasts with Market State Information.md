---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Local Estimation for Option Pricing: Improving Forecasts with Market State Information
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.federalreserve.gov/econres/feds/files/2025076pap.pdf)

## What Volta learned
Federal Reserve researchers keep standard option-pricing models (Heston-Nandi GARCH and Heston stochastic volatility) but fit them giving more weight to past days that look like today, measured by VIX, recent realized volatility or simply how recent the day is. On S&P 500 options (14-183 days to expiry, 2011-2023, tested out of sample 2015-2023), this beat the usual equal-weight fit: for the GARCH model the VIX-weighted fit had the lowest implied-volatility forecast error with a Diebold-Mariano t-stat of -5.85 against the benchmark. Gains were largest in calm periods like 2017 and small after 2019 or in high-volatility stretches.

## Why it matters (or not)
A sound modelling idea (let the model's settings depend on the current volatility regime), but it is about pricing 2-week-to-6-month SPX options, not next-day NQ moves, and the gains mostly faded after 2019.

## Concepts
local estimation, state-dependent parameters, heston-nandi garch, implied volatility forecasting, vix as state variable

## Idea
Let the brain's range forecast depend on the volatility regime: add the options-priced move and the 5-day range each multiplied by how high 30d IV is versus its own past, a crude stand-in for the paper's VIX-weighted fitting.

## Test
NO EDGE: range-forecast miss 0.557% -> 0.557% (+0.1%), better in 5/8 unseen years
How: z = l_iv30 minus its expanding mean (min 250 days, past data only); features l_bot*z and l_rng5*z. idea_lab cannot reweight training days, so this interaction is only an approximation of the paper's method.

Part of [[Research engine]]