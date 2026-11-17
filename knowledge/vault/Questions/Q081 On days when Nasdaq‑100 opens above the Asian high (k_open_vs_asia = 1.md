---
tags: [question, curiosity]
asked: 2026-11-17
---
# On days when Nasdaq‑100 opens above the Asian high (k_open_vs_asia = 1), does the session’s total range tend to be larger relative to its 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: Learning AI Agents, Market Makers, and Stress in Automated M; MODEL ADOPTION #4465: REJECT — LEDGER BENCH: Apply fi

Answer formula: `y_range / k_range20`
Predictor: `k_open_vs_asia`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: average 1.03, median 0.907 over 2906 sessions (2014-19: 1.03, 2020-25: 1.03). Predictor: lowest-fifth days 0.965 vs highest-fifth 1.08, skill +0.3% vs the base rate, better in 6/9 unseen years

Part of [[Questions Volta asked]]