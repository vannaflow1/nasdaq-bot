---
tags: [question, curiosity]
asked: 2026-10-23
---
# Does a wider forecasted high/low band improve the Sharpe of a 5‑minute breakout strategy?
Volta asked this itself. Inspired by: Volta's self-check: Quantify the incremental value of adding my range‑forecast high/low bands as a filter to any intraday entry idea.

Answer formula: `mean(y_return) - 0.5*std(y_return)`
Predictor: `rng - mean(rng, 252)`

[[TRANSLATION FAILED]] - TRANSLATION FAILED - IndexError: list index out of range

Part of [[Questions Volta asked]]