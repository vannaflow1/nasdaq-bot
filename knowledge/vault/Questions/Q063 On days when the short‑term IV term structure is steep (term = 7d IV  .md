---
tags: [question, curiosity]
asked: 2026-11-11
---
# On days when the short‑term IV term structure is steep (term = 7d IV / 30d IV > 1.2) and an event‑related implied move is unusually large (event_prem > 1), are we more likely to close the Nasdaq‑100 session above yesterday’s high?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Stock-level volatility forecasting using machine learning: A; Agentic AI in Automated Markets)

Answer formula: `y_closed_above_yday_high`
Predictor: `(term > 1.2) and (event_prem > 1)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 35% of 2808 sessions (2014-19: 35%, 2020-25: 35%). Predictor: lowest-fifth days 38% vs highest-fifth 32%, skill -0.3% vs the base rate, better in 3/9 unseen years

Part of [[Questions Volta asked]]