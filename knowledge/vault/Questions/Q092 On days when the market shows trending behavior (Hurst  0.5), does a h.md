---
tags: [question, curiosity]
asked: 2026-11-22
---
# On days when the market shows trending behavior (Hurst > 0.5), does a higher volatility risk premium (vrp) increase the probability that Nasdaq‑100 trades above the overnight high (y_took_overnight_high)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Replication package for: Arbitrage-Constrained Neural Interp; A Comparative Analysis of Volatility Predictions via 

Answer formula: `y_took_overnight_high`
Predictor: `where(k_hurst > 0.5, vrp, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 65% of 2907 sessions (2014-19: 65%, 2020-25: 65%). Predictor: lowest-fifth days 64% vs highest-fifth 65%, skill -0.2% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]