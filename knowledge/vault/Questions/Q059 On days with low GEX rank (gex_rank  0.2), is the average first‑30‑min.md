---
tags: [question, curiosity]
asked: 2026-11-10
---
# On days with low GEX rank (gex_rank < 0.2), is the average first‑30‑minute NQ return higher than on other days?
Volta asked this itself. Inspired by: Volta's self-check: Verify whether low GEX rank days produce larger first‑hour breakouts, which could be the missing link for a simple open‑breakout s

Answer formula: `y_first30_return`
Predictor: `where(gex_rank < 0.2, 1, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00915, median 0.0259 over 2907 sessions (2014-19: 0.00799, 2020-25: 0.0103). Predictor: lowest-fifth days 0.0183 vs highest-fifth 0.038, skill +0.0% vs the base rate, better in 5/9 unseen years

Part of [[Questions Volta asked]]