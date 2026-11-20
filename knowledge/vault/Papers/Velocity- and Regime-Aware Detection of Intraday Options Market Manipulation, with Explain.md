---
tags: [paper]
relevance: 2
read: 2026-11-20
---
# Velocity- and Regime-Aware Detection of Intraday Options Market Manipulation, with Explainable Attribution
★★☆☆☆  ·  OpenAlex  ·  [source](https://doi.org/10.1145/3858063.3858692)

## What Volta learned
The authors find that intraday manipulation in options leaves a distinct "pump‑and‑crash" pattern in the *velocity* of market state (option‑Delta velocity for index options) rather than in price levels, and that an autoencoder on minute‑level velocity can recover all regulator‑identified manipulation days. Adding regime information from a hidden Markov model hurts precision, and the signature seems to transfer across markets but its magnitude changes.

## Why it matters (or not)
Provides a novel detection idea that could inspire trader‑level alerts, but does not directly offer a tradable signal or model for market‑making.

## Concepts
option‑delta velocity, autoencoder anomaly detection, shap attribution, regime‑aware filtering, pump‑and‑crash signature

## Idea
Create a minute‑level feature of option‑Delta velocity for NQ options and flag days where the autoencoder reconstruction error exceeds a calibrated threshold; back‑test whether flagged days show abnormal next‑day returns (y_r) or range (y_rng).

## Test
not testable with my data yet

Part of [[Research engine]]