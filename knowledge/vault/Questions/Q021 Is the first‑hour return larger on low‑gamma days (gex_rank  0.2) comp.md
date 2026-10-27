---
tags: [question, curiosity]
asked: 2026-10-27
---
# Is the first‑hour return larger on low‑gamma days (gex_rank < 0.2) compared to other days?
Volta asked this itself. Inspired by: Volta's self-check: To verify whether the first‑15‑minute breakout signal gains extra edge on low‑gamma days, which could give a high‑probability trad

Answer formula: `y_first_hour_return`
Predictor: `where(gex_rank < 0.2, 1, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.00772, median 0.0202 over 2907 sessions (2014-19: 0.00451, 2020-25: 0.0109). Predictor: lowest-fifth days -0.0142 vs highest-fifth 0.0305, skill -0.0% vs the base rate, better in 6/9 unseen years

Part of [[Questions Volta asked]]