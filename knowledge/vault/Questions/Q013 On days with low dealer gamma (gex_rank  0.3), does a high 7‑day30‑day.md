---
tags: [question, curiosity]
asked: 2026-10-24
---
# On days with low dealer gamma (gex_rank < 0.3), does a high 7‑day/30‑day IV ratio (>1.2) predict a positive intraday return?
Volta asked this itself. Inspired by: Volta's self-check: Test if adding a short‑term term‑structure IV ratio improves the low‑gamma edge

Answer formula: `y_first_hour_return > 0`
Predictor: `where(gex_rank < 0.3, term, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 52% of 2907 sessions (2014-19: 52%, 2020-25: 52%). Predictor: lowest-fifth days 51% vs highest-fifth 50%, skill -0.0% vs the base rate, better in 5/9 unseen years

Part of [[Questions Volta asked]]