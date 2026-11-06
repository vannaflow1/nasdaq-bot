---
tags: [question, curiosity]
asked: 2026-11-06
---
# On days when SPX dealer gamma exposure is high (k_spx_gex above its median) and the NQ opened with a positive overnight gap (k_gap > 0), does the NQ first‑hour range tend to be larger relative to its 20‑day average range?
Volta asked this itself. Inspired by: Volta's own question (inspired by: A Deep Learning-Driven Operator Splitting Scheme for Free Bo; Stock-level volatility forecasting using machine lear

Answer formula: `y_first_hour_range / k_range20`
Predictor: `where(k_spx_gex > median(k_spx_gex), 1, 0) * where(k_gap > 0, 1, 0)`

[[TRANSLATION FAILED]] - TRANSLATION FAILED - IndexError: list index out of range

Part of [[Questions Volta asked]]