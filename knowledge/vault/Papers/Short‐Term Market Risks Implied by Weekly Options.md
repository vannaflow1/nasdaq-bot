---
tags: [paper]
relevance: 3
read: 2026-10-19
---
# Short‐Term Market Risks Implied by Weekly Options
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/jofi.12486)

## What Volta learned
Andersen, Fusari and Todorov (Journal of Finance, 2017) use weekly S&P 500 options, which mostly price the risk of sudden moves over the next few days, to measure how much the market fears a crash separately from overall volatility. They find this downside-jump fear moves on its own, is not captured by the VIX level, and helps predict future equity returns, so it can flag nervous periods that a calm volatility reading misses. Only the abstract was available, so the size of the effect is not known.

## Why it matters (or not)
Short-dated index options and crash fear are core to QQQ/NQ options trading, but I worked from the abstract only (no full text), and my rough proxy of 'crash fear not explained by volatility' showed nothing.

## Concepts
[[weekly options]], negative jump tail risk, crash fear vs volatility, [[return predictability]], short-dated spx options

## Idea
Proxy the paper's tail-fear factor as the part of 25d put skew not explained by 30d IV, and go long QQQ for the next day when it is above its past-year norm (higher tail fear earns a premium), short when below.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2226 signal days, hit 51.3% (always-long 56.6%), strategy -1.2 bps/day vs +0.6 for the same average exposure held constantly -> timing adds -1.8 bps/day, t=-0.57, positive in 6/9 years
How: long/short on `z(rr25 - (atm30 * 0.5), 252)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]