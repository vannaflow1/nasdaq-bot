---
tags: [question, curiosity]
asked: 2026-11-09
---
# On days when the market exhibits mean‑reverting behavior (Hurst < 0.5), does a larger volatility premium (vrp) make it more likely that the overnight gap is filled (y_gap_filled = 1)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Role of machine learning in financial economics; Evaluating Foundation Time-Series Models in Systematic Optio)

Answer formula: `y_gap_filled`
Predictor: `vrp * (k_hurst < 0.5)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 63% of 2808 sessions (2014-19: 63%, 2020-25: 62%). Predictor: lowest-fifth days 64% vs highest-fifth 62%, skill -0.4% vs the base rate, better in 3/9 unseen years

Part of [[Questions Volta asked]]