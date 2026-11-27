---
tags: [question, curiosity]
asked: 2026-11-27
---
# On days with gex_rank < 0.2, does the opening price of NQ tend to move toward the overnight high (k_on_high) or low (k_on_low) more often than on neutral‑gex days?
Volta asked this itself. Inspired by: Volta's self-check: Determine if low‑gex days create a systematic bias in the opening price toward the overnight high or low, which could be harvested

Answer formula: `y_on_open_bias`
Predictor: `gex_rank < 0.2 ? (on_high - open) < (open - on_low) ? 1 : -1 : 0`

[[TRANSLATION FAILED]] - TRANSLATION FAILED - SyntaxError: invalid syntax (<unknown>, line 1)

Part of [[Questions Volta asked]]