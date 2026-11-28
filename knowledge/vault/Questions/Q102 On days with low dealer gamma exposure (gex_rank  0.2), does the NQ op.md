---
tags: [question, curiosity]
asked: 2026-11-28
---
# On days with low dealer gamma exposure (gex_rank < 0.2), does the NQ opening price break yesterday's high more often?
Volta asked this itself. Inspired by: Volta's self-check: To quantify the hypothesized opening‑price bias on low‑gex days and see if it can serve as a trigger.

Answer formula: `y_took_yday_high`
Predictor: `where(gex_rank < 0.2, 1, 0)`

[[PROMISING]] - PROMISING (stress test: survived) : FACT: happens on 56% of 2808 sessions (2014-19: 57%, 2020-25: 55%). Predictor: lowest-fifth days 40% vs highest-fifth 59%, skill +2.8% vs the base rate, better in 8/9 unseen years

Part of [[Questions Volta asked]]