---
tags: [question, curiosity]
asked: 2026-11-14
---
# On days when a scheduled event has a large implied move (event_prem > 1) but the overnight gap is small relative to the typical NY range, are we more likely to close the Nasdaq‑100 session above yesterday's high?
Volta asked this itself. Inspired by: Volta's own question (inspired by: The Allocation of Talent: Implications for Growth; Learning AI Agents, Market Makers, and Stress in Automated M)

Answer formula: `y_closed_above_yday_high`
Predictor: `event_prem * (1 - abs(k_gap) / k_range20)`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 35% of 2808 sessions (2014-19: 35%, 2020-25: 35%). Predictor: lowest-fifth days 28% vs highest-fifth 41%, skill +0.4% vs the base rate, better in 5/9 unseen years

Part of [[Questions Volta asked]]