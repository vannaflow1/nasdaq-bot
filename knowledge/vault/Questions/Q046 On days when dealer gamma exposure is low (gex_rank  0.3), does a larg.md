---
tags: [question, curiosity]
asked: 2026-11-04
---
# On days when dealer gamma exposure is low (gex_rank < 0.3), does a larger pre‑open red‑folder surprise (k_red_surprise) cause a disproportionately larger NY range relative to its 20‑day average (y_range / k_range20) compared to higher‑gamma days?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Latent Continuum of Regimes in Limit Order Book Dynamics; Synthetic American Option Pricing via Jump-HMM-Driven Hes

Answer formula: `y_range / k_range20`
Predictor: `where(gex_rank < 0.3, k_red_surprise, k_red_surprise * 0.5)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 1.03, median 0.907 over 2906 sessions (2014-19: 1.03, 2020-25: 1.03). Predictor: lowest-fifth days 1.08 vs highest-fifth 0.978, skill -0.3% vs the base rate, better in 3/7 unseen years

Part of [[Questions Volta asked]]