---
tags: [paper]
relevance: 4
read: 2026-11-22
---
# Diffusion models for dynamic volatility surface generation and data-driven hedging
★★★★☆  ·  OpenAlex  ·  [source](https://doi.org/10.1145/3858063.3858716)

## What Volta learned
The paper proposes diffusion‑model based generators (AD‑Seq‑Vol and AD‑Seq‑Vol‑FT) that sequentially produce realistic, arbitrage‑free SPX implied‑volatility surfaces, and shows that hedging based on these generated scenarios yields near‑zero tracking error and lower tail risk versus traditional methods.

## Why it matters (or not)
Abstract only; no quantitative results provided, but the method directly targets SPX surface generation and hedging, which is highly relevant for options traders.

## Concepts
diffusion models, implied volatility surface simulation, no‑arbitrage penalties, scenario‑based hedging, tail‑risk reduction

## Idea
Train a diffusion‑model (similar to AD‑Seq‑Vol‑FT) on the daily SPX surface data in Volta's memory, generate next‑day scenario surfaces, and use them in a rolling‑horizon optimization to compute hedge ratios for the next‑day NQ/QQQ positions; compare tracking error and tail risk against the current gamma‑neutral or delta‑hedge baseline.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires generating full daily volatility surface scenarios with a diffusion model and performing a rolling‑horizon portfolio optimization to compute hedge ratios, which needs intraday option price matrices and simulation of hedging trades. Volta only provides aggregated surface statistics (iv30, atm7, atm30, rr25, bf25, etc.) and cannot represent the diffusion‑model generated surfaces or the resulting hedge‑ratio calculations.

Part of [[Research engine]]