---
tags: [paper]
relevance: 3
read: 2026-11-23
---
# PIRanNN: Random-Feature Pricing and Calibration under Jump-Diffusion and Stochastic-Volatility Models
★★★☆☆  ·  OpenAlex  ·  [source](https://arxiv.org/pdf/2611.19792)

## What Volta learned
The paper presents PIRanNN, a random‑feature (extreme learning machine) method that solves the pricing PDE/PIDE for European options under jump‑diffusion (Merton, Kou) and stochastic‑volatility (Heston, SABR) models in one linear least‑squares solve, yielding prices, Greeks and exact price‑sensitivities to model parameters for fast gradient‑based calibration. Subtracting a Black‑Scholes baseline dramatically reduces pricing error (≈100× for jumps), making calibrated jump parameters accurate to within ~3% versus errors up to 50% without the subtraction.

## Why it matters (or not)
Provides a fast, analytic‑gradient pricing tool for jump and SV models that could improve calibration speed and accuracy for traders using options data.

## Concepts
random‑feature extreme learning machine, jump‑diffusion pricing, analytic jump integral, black‑scholes subtraction, gradient‑based calibration

## Idea
Use PIRanNN to price and compute Greeks for NQ (Nasdaq) options under a Merton jump‑diffusion model, then calibrate the jump intensity and volatility parameters daily using our daily option‑price columns (IV term, Heston fit, etc.), and compare the calibrated parameters to those obtained from a standard finite‑difference solver.

## Test
[[DOESN'T FIT]] - DOESN'T FIT MY DATA - The idea requires daily full option‑price surfaces and a calibrated jump‑diffusion model, which need per‑strike option data and a pricing engine that Volta does not provide. Only aggregated implied vol metrics (atm7, atm30, etc.) and Heston parameters are available, insufficient for calibrating a Merton jump‑diffusion model each day.

Part of [[Research engine]]