---
tags: [paper]
relevance: 3
read: 2026-10-25
---
# GROMM: Generative Risk-neutral Option Market Models
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2610.16732v2)

## What Volta learned
GROMM is a generative, arbitrage‑free model that represents the whole S&P index option surface as a smooth grid of discrete local volatilities and learns their joint dynamics under both the real‑world (P) and risk‑neutral (Q) measures. It fits >95% of daily quotes (including next‑day expiries) inside the bid‑ask spread and provides an explicit risk‑neutral drift, allowing fully consistent simulation of future option surfaces.

## Why it matters (or not)
The paper offers a new way to model and simulate the whole S&P option surface, which is useful for pricing, hedging and scenario analysis, but it does not directly propose a trading strategy.

## Concepts
arbitrage‑free option surface, discrete local volatility grid, risk‑neutral dynamics, real‑world dynamics, static and dynamic no‑arbitrage tests

## Idea
Use the GROMM‑generated risk‑neutral variance for the next‑day expiry as a forecast of the NQ (Nasdaq) intraday range, and go long (short) NQ futures when the model‑implied variance is significantly above (below) the historical average of l_rng.

## Test
queued for testing

Part of [[Research engine]]