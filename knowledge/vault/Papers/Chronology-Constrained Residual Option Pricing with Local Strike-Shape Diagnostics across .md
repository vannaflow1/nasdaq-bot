---
tags: [paper]
relevance: 2
read: 2026-10-20
---
# Chronology-Constrained Residual Option Pricing with Local Strike-Shape Diagnostics across BTC and ETH Windows
★★☆☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.70267/icrafm.202617541548)

## What Volta learned
The paper compares several option pricing models, including a chronology‑constrained residual network (CCRP), against Black‑Scholes, SVI and simple benchmarks on 24‑hour BTC and ETH option windows, and finds no consistent winner and mixed arbitrage‑consistency results.

## Why it matters (or not)
Focuses on crypto options rather than Nasdaq/S&P futures, offering limited direct insight for typical equity option traders.

## Concepts
residual learning, chronology‑constrained training, cryptocurrency options, arbitrage diagnostics, model comparison

## Idea
Implement the CCRP model on our daily Deribit BTC/ETH option data (using l_bot, l_impl, gex_rank, etc.) and compare its out‑of‑sample RMSE and arbitrage violations to Black‑Scholes and SVI over rolling 24‑hour windows.

## Test
not testable with my data yet

Part of [[Research engine]]