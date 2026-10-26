---
tags: [question, curiosity]
asked: 2026-10-26
---
# On days when the market’s implied overnight move (impl) is larger than the observed overnight range (k_on_range), are we more likely to see NQ trade above the overnight high (y_took_overnight_high) during the NY session?
Volta asked this itself. Inspired by: Volta's own question (inspired by: LiveOption: Evaluating LLM Agents in Structured Option Tradi; Do Options-Flow Signatures of Dealer Hedging Predict 

Answer formula: `y_took_overnight_high`
Predictor: `impl / k_on_range`

[[PROMISING]] - PROMISING (stress test: survived) : FACT: happens on 65% of 2907 sessions (2014-19: 65%, 2020-25: 65%). Predictor: lowest-fifth days 49% vs highest-fifth 74%, skill +3.1% vs the base rate, better in 9/9 unseen years

Part of [[Questions Volta asked]]