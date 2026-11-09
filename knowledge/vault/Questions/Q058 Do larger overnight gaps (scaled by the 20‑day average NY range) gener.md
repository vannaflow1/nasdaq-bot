---
tags: [question, curiosity]
asked: 2026-11-09
---
# Do larger overnight gaps (scaled by the 20‑day average NY range) generate larger first‑hour returns in the NQ session?
Volta asked this itself. Inspired by: Volta's own question (inspired by: MODEL ADOPTION #4465: REJECT — LEDGER BENCH: Apply filter: S; Evaluating Foundation Time-Series Models in Systemati

Answer formula: `y_first_hour_return / k_range20`
Predictor: `k_gap / k_range20`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00311, median 0.0157 over 2906 sessions (2014-19: 0.00253, 2020-25: 0.00368). Predictor: lowest-fifth days -0.0272 vs highest-fifth 0.0214, skill -0.1% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]