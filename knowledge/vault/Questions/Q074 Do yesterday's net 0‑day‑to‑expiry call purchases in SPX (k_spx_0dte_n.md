---
tags: [question, curiosity]
asked: 2026-11-15
---
# Do yesterday's net 0‑day‑to‑expiry call purchases in SPX (k_spx_0dte_net_calls_yday − k_spx_0dte_net_puts_yday) predict a larger first‑hour return of the Nasdaq‑100 relative to its typical range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Role of machine learning in financial economics; Towards Robust Reinforcement Learning Market Making: Lessons)

Answer formula: `y_first_hour_return / k_range20`
Predictor: `(k_spx_0dte_net_calls_yday - k_spx_0dte_net_puts_yday)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00311, median 0.0157 over 2906 sessions (2014-19: 0.00253, 2020-25: 0.00368). Predictor: lowest-fifth days -0.00581 vs highest-fifth -0.0137, skill -1.9% vs the base rate, better in 1/4 unseen years

Part of [[Questions Volta asked]]