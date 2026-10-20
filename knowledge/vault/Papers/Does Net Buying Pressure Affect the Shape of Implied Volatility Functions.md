---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Does Net Buying Pressure Affect the Shape of Implied Volatility Functions?
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/j.1540-6261.2004.00647.x)

## What Volta learned
Bollen and Whaley show that implied volatility moves with public order flow: when more customers buy options than sell them, implied vol rises, so the shape of the volatility smile is partly driven by demand, not only by expected risk. For S&P 500 index options the biggest driver is buying pressure in index puts, while for single-stock options it is call demand. Delta-neutral option-writing strategies earned abnormal returns roughly matching how far implied vol sat above realized vol. Worked from the abstract only (no full text in the repo), so no specific numbers are available.

## Why it matters (or not)
Directly about index option pricing and why put skew is rich, which matters for reading QQQ/NDX skew, but Volta has no order-flow data, and a skew-based proxy did not improve the range forecast.

## Concepts
net buying pressure, [[implied volatility smile]], index put demand, limits to arbitrage, option writing premium

## Idea
Use the put skew level and its 5-day change as a proxy for index put buying pressure and add them to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.532% (-0.2%), better in 4/9 unseen years
How: Built from same-day-close skew column: skew and skew minus its value 5 sessions earlier; a side test going long QQQ when skew is in its top past-year 20% also showed no edge (t=0.71).

Part of [[Research engine]]