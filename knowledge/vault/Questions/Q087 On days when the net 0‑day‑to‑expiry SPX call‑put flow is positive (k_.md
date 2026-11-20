---
tags: [question, curiosity]
asked: 2026-11-20
---
# On days when the net 0‑day‑to‑expiry SPX call‑put flow is positive (k_spx_0dte_net_calls_yday − k_spx_0dte_net_puts_yday > 0), does Nasdaq‑100 close above yesterday’s high more often?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Towards Robust Reinforcement Learning Market Making: Lessons; A Review of Methods for Predicting Stock Volatility: 

Answer formula: `y_closed_above_yday_high`
Predictor: `(k_spx_0dte_net_calls_yday - k_spx_0dte_net_puts_yday)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 35% of 2808 sessions (2014-19: 35%, 2020-25: 35%). Predictor: lowest-fifth days 26% vs highest-fifth 40%, skill -0.1% vs the base rate, better in 3/4 unseen years

Part of [[Questions Volta asked]]