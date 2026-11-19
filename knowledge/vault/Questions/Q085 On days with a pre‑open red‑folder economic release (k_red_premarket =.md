---
tags: [question, curiosity]
asked: 2026-11-19
---
# On days with a pre‑open red‑folder economic release (k_red_premarket = 1), does a larger surprise (k_red_surprise) make it more likely that the overnight gap is filled (y_gap_filled = 1), especially when the market is trending (Hurst > 0.5)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Conditional Deep Lévy Models for Exotic Derivatives: History; Evaluating Foundation Time-Series Models in Systemati

Answer formula: `y_gap_filled`
Predictor: `k_red_surprise * where(k_hurst > 0.5, 1, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 63% of 2808 sessions (2014-19: 63%, 2020-25: 62%). Predictor: lowest-fifth days 66% vs highest-fifth 51%, skill -1.9% vs the base rate, better in 3/7 unseen years

Part of [[Questions Volta asked]]