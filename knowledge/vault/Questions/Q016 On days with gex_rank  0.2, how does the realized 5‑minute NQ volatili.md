---
tags: [question, curiosity]
asked: 2026-10-25
---
# On days with gex_rank < 0.2, how does the realized 5‑minute NQ volatility (standard deviation of returns) compare to the overall sample?
Volta asked this itself. Inspired by: Volta's self-check: Validate the hypothesised link between low dealer gamma and reduced intraday volatility, which could justify tighter stops and hig

Answer formula: `mean(r5_min_vol|gex_rank<0.2) / mean(r5_min_vol)`
Predictor: `r5_min_vol = stdev(ret_1m, 5)`

[[TRANSLATION FAILED]] - TRANSLATION FAILED - SyntaxError: invalid syntax (<unknown>, line 1)

Part of [[Questions Volta asked]]