---
tags: [question, curiosity]
asked: 2026-11-01
---
# On days when only NQ (and not ES) captures the Asia high before the NY open (k_smt_high_nq_only = 1), does the intraday NY range exceed its 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: A Deep Learning-Driven Operator Splitting Scheme for Free Bo; Stock-level volatility forecasting using machine lear

Answer formula: `y_range / k_range20`
Predictor: `k_smt_high_nq_only`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 1.03, median 0.907 over 2906 sessions (2014-19: 1.03, 2020-25: 1.03). Predictor: lowest-fifth days 1.04 vs highest-fifth 0.995, skill -0.1% vs the base rate, better in 5/9 unseen years

Part of [[Questions Volta asked]]