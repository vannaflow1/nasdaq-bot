---
tags: [question, curiosity]
asked: 2026-10-28
---
# When the S&P 500 is close to its gamma‑flip level (small |k_spx_flip_dist|), does NQ tend to post a larger first‑hour return relative to its typical range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: GROMM: Generative Risk-neutral Option Market Models; Valuation Engines Under Market Incompleteness: An Empirical )

Answer formula: `y_first_hour_return / k_range20`
Predictor: `abs(k_spx_flip_dist)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00311, median 0.0157 over 2906 sessions (2014-19: 0.00253, 2020-25: 0.00368). Predictor: lowest-fifth days 0.0109 vs highest-fifth 0.00895, skill -0.3% vs the base rate, better in 2/5 unseen years

Part of [[Questions Volta asked]]