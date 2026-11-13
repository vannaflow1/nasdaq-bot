---
tags: [question, curiosity]
asked: 2026-11-13
---
# On days when Nasdaq‑100 opens with a relatively large positive overnight gap (greater than 0.5% of the prior close), is the first‑hour range disproportionately larger than its 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Role of machine learning in financial economics; Latent Continuum of Regimes in Limit Order Book Dynamics)

Answer formula: `y_first_hour_range / k_range20`
Predictor: `k_gap > 0.005`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.58, median 0.518 over 2906 sessions (2014-19: 0.584, 2020-25: 0.577). Predictor: lowest-fifth days 0.547 vs highest-fifth 0.628, skill +1.8% vs the base rate, better in 6/9 unseen years

Part of [[Questions Volta asked]]