---
tags: [question, curiosity]
asked: 2026-11-08
---
# On days when the implied move for a scheduled event is unusually large (event_prem > 1), does NQ tend to post a larger first‑hour return relative to its typical 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Stock-level volatility forecasting using machine learning: A; The Allocation of Talent: Implications for Growth)

Answer formula: `y_first_hour_return / k_range20`
Predictor: `event_prem > 1`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00311, median 0.0157 over 2906 sessions (2014-19: 0.00253, 2020-25: 0.00368). Predictor: lowest-fifth days 0.021 vs highest-fifth -0.00486, skill -0.1% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]