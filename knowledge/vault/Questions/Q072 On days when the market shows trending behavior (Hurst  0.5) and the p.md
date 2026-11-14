---
tags: [question, curiosity]
asked: 2026-11-14
---
# On days when the market shows trending behavior (Hurst > 0.5) and the pre‑open red‑folder surprise is positive, does the first‑hour NQ return relative to the first‑hour range become larger?
Volta asked this itself. Inspired by: Volta's own question (inspired by: The Allocation of Talent: Implications for Growth; Role of machine learning in financial economics)

Answer formula: `y_first_hour_return / y_first_hour_range`
Predictor: `k_hurst * k_red_surprise`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.0312, median 0.0373 over 2907 sessions (2014-19: 0.0307, 2020-25: 0.0317). Predictor: lowest-fifth days 0.0101 vs highest-fifth 0.0579, skill +0.0% vs the base rate, better in 5/6 unseen years

Part of [[Questions Volta asked]]