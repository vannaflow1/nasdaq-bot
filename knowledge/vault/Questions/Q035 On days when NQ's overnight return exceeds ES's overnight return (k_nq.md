---
tags: [question, curiosity]
asked: 2026-10-31
---
# On days when NQ's overnight return exceeds ES's overnight return (k_nq_minus_es_on > 0), does NQ achieve a higher daily return (y_return) compared to its average overnight return (k_on_return)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Synthetic American Option Pricing via Jump-HMM-Driven Heston; Do Options-Flow Signatures of Dealer Hedging Predict 

Answer formula: `y_return / k_on_return`
Predictor: `k_nq_minus_es_on`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 0.161, median 0 over 2895 sessions (2014-19: -0.00954, 2020-25: 0.327). Predictor: lowest-fifth days 1.3 vs highest-fifth 0.195, skill -0.2% vs the base rate, better in 3/9 unseen years

Part of [[Questions Volta asked]]