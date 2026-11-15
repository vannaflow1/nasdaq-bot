---
tags: [question, curiosity]
asked: 2026-11-15
---
# On days when a red‑folder economic release occurs during the session (k_red_session = 1) and the market shows trending behavior (Hurst > 0.5), does a larger pre‑open surprise (k_red_surprise) lead to a higher first‑hour Nasdaq‑100 return?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Agentic AI in Automated Markets; Statistical Modelling of Stock-Market Volatility Forecasting)

Answer formula: `y_first_hour_return`
Predictor: `k_red_session * (k_hurst > 0.5) * k_red_surprise`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00772, median 0.0202 over 2907 sessions (2014-19: 0.00451, 2020-25: 0.0109). Predictor: lowest-fifth days 0.0805 vs highest-fifth -0.0868, skill -0.2% vs the base rate, better in 2/6 unseen years

Part of [[Questions Volta asked]]