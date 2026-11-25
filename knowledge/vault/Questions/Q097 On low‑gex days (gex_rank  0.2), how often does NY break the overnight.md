---
tags: [question, curiosity]
asked: 2026-11-25
---
# On low‑gex days (gex_rank < 0.2), how often does NY break the overnight high within the first 30 minutes?
Volta asked this itself. Inspired by: Volta's self-check: To quantify how low‑gex days affect the probability and size of the opening range breakout, a prerequisite for a viable entry rule

Answer formula: `where(y_took_overnight_high and y_high_minute <= 30, 1, 0)`
Predictor: `where(gex_rank < 0.2, 1, 0)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 11% of 2972 sessions (2014-19: 10%, 2020-25: 12%). Predictor: lowest-fifth days 7% vs highest-fifth 9%, skill +0.2% vs the base rate, better in 6/9 unseen years

Part of [[Questions Volta asked]]