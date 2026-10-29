---
tags: [question, curiosity]
asked: 2026-10-29
---
# On days with a positive CPI surprise (k_cpi_surprise > 0), is the NQ intraday high more likely to be set within the first hour (y_high_minute ≤ 60) compared to days without a positive surprise?
Volta asked this itself. Inspired by: Volta's own question (inspired by: LiveOption: Evaluating LLM Agents in Structured Option Tradi; Do Options-Flow Signatures of Dealer Hedging Predict 

Answer formula: `where(y_high_minute <= 60, 1, 0)`
Predictor: `k_cpi_surprise > 0`

[[TRANSLATION FAILED]] - TRANSLATION FAILED - formula gives too little usable data

Part of [[Questions Volta asked]]