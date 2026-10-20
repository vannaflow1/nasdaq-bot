---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Model Specification and Risk Premia: Evidence from Futures Options
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/j.1540-6261.2007.01241.x)

## What Volta learned
Using S&P 500 futures option prices from 1987 to 2003, the authors find strong evidence that both prices and volatility itself can jump, not just drift smoothly. They also find that investors pay a sizeable, statistically significant premium for protection against those jumps, and say this jump premium is key to understanding why options (especially puts) earn the returns they do. Worked from the abstract only (no full text in the repo), so the size of the premia is not given.

## Why it matters (or not)
Explains why index puts are usually overpriced relative to realized moves, useful background for NQ/QQQ option selling or buying, but it is about long-run option pricing (data ends 2003), not a next-day signal; abstract only.

## Concepts
jump risk premium, volatility jumps, diffusive risk premium, s&p futures options, [[model specification]]

## Idea
Jump-fear premium as a buy signal: hold QQQ long the next day only when put skew (25d put-call IV / ATM IV) is above its trailing one-year median, flat otherwise.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1084 signal days, hit 57.7% (always-long 57.7%), strategy +2.8 bps/day vs +3.6 for the same average exposure held constantly -> timing adds -0.8 bps/day, t=-0.50, positive in 5/9 years
How: long/flat on `where(rank(skew, 252) > 0.5, 1, 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]