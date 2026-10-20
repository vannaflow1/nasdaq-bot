---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# Two are better than one: Volatility forecasting using multiplicative component GARCH‐MIDAS models
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/jae.2742)

## What Volta learned
This paper (Conrad and Kleen) studies GARCH-MIDAS models, which split market volatility into a fast-moving short-term part and a slow long-term part driven by an economic series, and works out their statistical properties. On S&P 500 data, the version whose long-term part is driven by US housing starts beat many rival models (HAR, realized GARCH, HEAVY, regime-switching GARCH) when forecasting volatility 2 and 3 months ahead. Only the abstract was available, so the size of the improvement is not known.

## Why it matters (or not)
Worked from the abstract only; the gains are at 2-3 month horizons, far from next-day NQ ranges, and a slow long-term volatility component added nothing to my next-day forecast.

## Concepts
garch-midas, long- and short-term volatility components, macro-driven volatility, [[volatility forecasting]], s&p 500

## Idea
Add a slow long-term volatility component (the average NQ daily range over the last 120 trading days, in logs) to the next-day range forecast, next to the existing 1-, 5- and 20-day ranges.

## Test
NO EDGE: range-forecast miss 0.530% -> 0.531% (-0.2%), better in 4/9 unseen years
How: l_rng120 = log of the trailing 120-day mean of exp(l_rng), past data only; adding a 250-day version too was also NO EDGE (0.557% -> 0.557%, 3/8 years). The paper's housing-starts driver is not in my memory.

Part of [[Research engine]]