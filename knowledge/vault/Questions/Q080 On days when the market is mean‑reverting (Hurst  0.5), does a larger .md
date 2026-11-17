---
tags: [question, curiosity]
asked: 2026-11-17
---
# On days when the market is mean‑reverting (Hurst < 0.5), does a larger volatility risk premium (vrp) increase the probability that the overnight gap is filled (y_gap_filled = 1)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Towards Robust Reinforcement Learning Market Making: Lessons; Evaluating Foundation Time-Series Models in Systemati

Answer formula: `y_gap_filled`
Predictor: `where(k_hurst < 0.5, vrp, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 63% of 2808 sessions (2014-19: 63%, 2020-25: 62%). Predictor: lowest-fifth days 65% vs highest-fifth 61%, skill -0.6% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]