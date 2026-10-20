---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# Volatility Parametrizations with Random Coefficients: Analytic Flexibility for Implied Volatility Surfaces
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2411.04041)

## What Volta learned
Standard curve formulas used to describe the implied-volatility smile (SABR, SVI) often cannot match very short-dated options, so the authors let one formula parameter be random, which turns the smile into a blend of two curves while staying arbitrage-free and fast to compute. On SPX options on 31 July 2024, the fitting error for the August 2024 expiry fell from 4.8e-4 (regular SABR) to 1.2e-5 (randomized SABR), and the needed randomness shrank as expiry got longer. A variant that randomizes the spot price fits the W-shaped smiles seen in near-expiry AMZN options on an earnings day (April 2018), when the market prices two possible outcomes.

## Why it matters (or not)
A curve-fitting tool for option quants; it can help read event-day smiles (two-humped price outcomes before earnings), but it gives no next-day signal for NQ/QQQ and the evidence is a few snapshot days.

## Concepts
[[implied volatility smile]], sabr parametrization, randomized parameters, bimodal risk-neutral distribution, earnings-day options

## Idea
The method needs full option chains per strike and expiry to fit smiles; my memory has only summary readings (ATM IV, 25-delta skew, term ratio), so smile shape (e.g. W-shapes before events) cannot be measured.

## Test
not testable with my data yet

Part of [[Research engine]]