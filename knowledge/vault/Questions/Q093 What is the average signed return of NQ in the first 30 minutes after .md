---
tags: [question, curiosity]
asked: 2026-11-23
---
# What is the average signed return of NQ in the first 30 minutes after the open on days with gex_rank < 0.2 compared to all other days?
Volta asked this itself. Inspired by: Volta's self-check: Quantify the average opening‑price drift and early‑session return on low‑GEX days to design a simple rule (e.g., long if open > ye

Answer formula: `y_first30_return`
Predictor: `gex_rank`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00915, median 0.0259 over 2907 sessions (2014-19: 0.00799, 2020-25: 0.0103). Predictor: lowest-fifth days 0.011 vs highest-fifth -0.0221, skill -0.1% vs the base rate, better in 3/9 unseen years

Part of [[Questions Volta asked]]