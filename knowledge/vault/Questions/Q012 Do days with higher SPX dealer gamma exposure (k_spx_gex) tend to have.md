---
tags: [question, curiosity]
asked: 2026-10-23
---
# Do days with higher SPX dealer gamma exposure (k_spx_gex) tend to have a relatively smaller NQ intraday range (y_range) compared to its 20‑day average (k_range20)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Neural Control Variates for Variance Reduction; Valuation Engines Under Market Incompleteness: An Empirical )

Answer formula: `y_range / k_range20`
Predictor: `k_spx_gex`

[[PROMISING]] - PROMISING (stress test: survived) : FACT: average 1.03, median 0.907 over 2906 sessions (2014-19: 1.03, 2020-25: 1.03). Predictor: lowest-fifth days 0.833 vs highest-fifth 1.22, skill +7.4% vs the base rate, better in 4/5 unseen years

Part of [[Questions Volta asked]]