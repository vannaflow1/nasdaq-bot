---
tags: [question, curiosity]
asked: 2026-11-22
---
# On days with low dealer gamma exposure (gex_rank < 0.2), what is the average signed return from open to the 15‑minute extreme (high minus low) and to the daily close?
Volta asked this itself. Inspired by: Volta's self-check: Quantify the strength of the low‑gex opening‑price edge and see if it can be turned into a simple breakout rule.

Answer formula: `(y_up_from_open - y_down_from_open) + y_return`
Predictor: `where(gex_rank < 0.2, 1, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average -0.0256, median 0.0974 over 2907 sessions (2014-19: -0.0391, 2020-25: -0.0124). Predictor: lowest-fifth days 0.144 vs highest-fifth 0.144, skill +0.0% vs the base rate, better in 5/9 unseen years

Part of [[Questions Volta asked]]