---
tags: [question, curiosity]
asked: 2026-10-24
---
# On days with a pre‑open red‑folder event (k_red_premarket = 1), does a larger surprise magnitude (k_red_surprise) lead to a proportionally larger actual move relative to the options‑priced move (impl)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Some Control Variates for exotic options; The impact of option hedging on the spot market volatility)

Answer formula: `y_return / impl`
Predictor: `k_red_surprise * k_red_premarket`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 2.88, median 11.3 over 2907 sessions (2014-19: 3.61, 2020-25: 2.16). Predictor: lowest-fifth days 24.1 vs highest-fifth 0.515, skill -0.4% vs the base rate, better in 6/7 unseen years

Part of [[Questions Volta asked]]