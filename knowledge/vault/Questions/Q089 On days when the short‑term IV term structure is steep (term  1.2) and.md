---
tags: [question, curiosity]
asked: 2026-11-21
---
# On days when the short‑term IV term structure is steep (term > 1.2) and the overnight range is unusually small (k_on_range < 0.5 × k_range20), are we more likely to see Nasdaq‑100 close above yesterday’s high (y_closed_above_yday_high = 1)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Velocity- and Regime-Aware Detection of Intraday Options Mar; The Term Structure of Implied Fee Rates in Liquidity 

Answer formula: `y_closed_above_yday_high`
Predictor: `(term > 1.2) * (k_on_range < 0.5 * k_range20)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 35% of 2808 sessions (2014-19: 35%, 2020-25: 35%). Predictor: lowest-fifth days 38% vs highest-fifth 33%, skill -0.3% vs the base rate, better in 2/9 unseen years

Part of [[Questions Volta asked]]