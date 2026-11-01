---
tags: [question, curiosity]
asked: 2026-11-01
---
# Is the volatility premium (vrp) more predictive of the first‑hour NQ return on trending days (Hurst > 0.5) than on mean‑reverting days (Hurst ≤ 0.5)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Latent Continuum of Regimes in Limit Order Book Dynamics; Range-Based Volatility Estimation and Forecasting)

Answer formula: `y_first_hour_return`
Predictor: `vrp * where(k_hurst > 0.5,1,0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00772, median 0.0202 over 2907 sessions (2014-19: 0.00451, 2020-25: 0.0109). Predictor: lowest-fifth days 0.012 vs highest-fifth -0.0307, skill -0.2% vs the base rate, better in 2/9 unseen years

Part of [[Questions Volta asked]]