---
tags: [question, curiosity]
asked: 2026-11-25
---
# On days when the short‑term IV term structure is steep (term > 1.1) but the implied event move is modest (event_prem ≤ 1), does the Nasdaq‑100 session range tend to be larger relative to its 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Arbitrage-Free Implied Volatility Surface Reconstruction via; Arithmetic Models for Commodity Futures, Vanilla, and

Answer formula: `y_range / k_range20`
Predictor: `term * (1 - clip(event_prem, 0, 1))`

[[PROMISING]] - PROMISING (stress test: survived) : FACT: average 1.03, median 0.907 over 2906 sessions (2014-19: 1.03, 2020-25: 1.03). Predictor: lowest-fifth days 0.916 vs highest-fifth 1.29, skill +7.3% vs the base rate, better in 9/9 unseen years

Part of [[Questions Volta asked]]