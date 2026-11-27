---
tags: [paper]
relevance: 3
read: 2026-11-27
---
# Overreaction to volatility shock and option returns
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://repository.hkust.edu.hk/ir/bitstream/1783.1-141007/1/991013223059303412.pdf)

## What Volta learned
The thesis studies how market participants overreact to sudden changes in implied volatility and how that affects subsequent option returns.

## Why it matters (or not)
Only the abstract is available, so concrete models or quantitative findings are missing.

## Concepts
volatility shock, [[option returns]], investor overreaction, implied volatility dynamics, behavioral bias

## Idea
Identify days with a large one‑day jump in 30‑day ATM IV (e.g., >2 σ) and test whether options (especially out‑of‑the‑money calls/puts) earn abnormal returns in the following 5‑10 days, controlling for delta and gamma exposure.

## Test
NOT TESTABLE (fewer than 100 trade days)
How: `where(z(iv30 - lag(iv30,1),252) > 2, -1, 0)`: > 0 sell volatility (QQQ iron fly, wings 2x the straddle), < 0 buy the straddle, else no trade
Touches: [[Short-vol strategy]]

Part of [[Research engine]]