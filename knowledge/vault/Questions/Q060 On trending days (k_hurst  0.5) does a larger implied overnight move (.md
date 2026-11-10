---
tags: [question, curiosity]
asked: 2026-11-10
---
# On trending days (k_hurst > 0.5) does a larger implied overnight move (impl) translate into a proportionally larger first‑hour return compared to mean‑reverting days?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Statistical Modelling of Stock-Market Volatility Forecasting; Role of machine learning in financial economics)

Answer formula: `y_first_hour_return / impl`
Predictor: `sign(k_hurst - 0.5)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average -0.00427, median 2.64 over 2907 sessions (2014-19: -0.151, 2020-25: 0.14). Predictor: lowest-fifth days -0.361 vs highest-fifth 0.0179, skill -0.4% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]