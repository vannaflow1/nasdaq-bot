---
tags: [paper]
relevance: 2
read: 2026-11-22
---
# Replication package for: Arbitrage-Constrained Neural Interpolation of the Implied Volatility Surface: Evidence from NSE Index Options
★★☆☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.5281/zenodo.23728871)

## What Volta learned
The paper introduces PNmix, a neural‑network based method that builds an implied volatility surface while guaranteeing no butterfly or calendar arbitrage. It is benchmarked against classic parametrizations (SVI, SSVI, splines) on NSE index options from 2020‑2026 and includes an intraday backtest.

## Why it matters (or not)
The method is about constructing arbitrage‑free volatility surfaces, which is generally useful but the paper focuses on NSE data and does not provide results for US equity index options.

## Concepts
[[arbitrage‑free iv surface]], neural interpolation, svi benchmark, expanding‑origin validation, intraday backtest

## Idea
Fit the PNmix neural surface to daily QQQ option data (using columns like l_impl, l_iv30, term, skew, gex_rank) and compare its out‑of‑sample pricing error to standard SVI/SSVI fits; if PNmix yields lower error, use its implied vol predictions for a delta‑neutral straddle trading signal.

## Test
not testable with my data yet

Part of [[Research engine]]