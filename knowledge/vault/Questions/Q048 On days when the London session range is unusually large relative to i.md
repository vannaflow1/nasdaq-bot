---
tags: [question, curiosity]
asked: 2026-11-05
---
# On days when the London session range is unusually large relative to its 20‑day average, are first‑hour NQ ranges disproportionately larger than the typical 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: The Allocation of Talent: Implications for Growth; Role of machine learning in financial economics)

Answer formula: `y_first_hour_range / k_range20`
Predictor: `k_london_range / k_range20`

[[PROMISING]] - PROMISING (stress test: survived) : FACT: average 0.58, median 0.518 over 2906 sessions (2014-19: 0.584, 2020-25: 0.577). Predictor: lowest-fifth days 0.455 vs highest-fifth 0.756, skill +20.3% vs the base rate, better in 9/9 unseen years

Part of [[Questions Volta asked]]