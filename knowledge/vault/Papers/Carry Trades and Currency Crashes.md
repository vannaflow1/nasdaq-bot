---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Carry Trades and Currency Crashes
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](http://www.nber.org/papers/w14473.pdf)

## What Volta learned
Brunnermeier, Nagel and Pedersen show that the currency carry trade (borrow in low-rate currencies like the yen, invest in high-rate ones like the Australian dollar) earns small steady gains but carries crash risk: its returns are negatively skewed, and across currencies the link between interest-rate gap and skewness is very tight (R-squared of 81%). The crashes come from sudden unwinds when risk appetite and funding liquidity dry up, for example in weeks when the VIX or the TED spread rises. After carry losses, speculators hold smaller positions and pay more for crash insurance (risk reversals), and future crash risk actually falls. Read from the repo's full text.

## Why it matters (or not)
An FX paper, but its 'crowded positions unwind when VIX jumps' mechanism and 'insurance is priciest right after losses' point echo index options; my equity translation of the post-loss signal did not work.

## Concepts
carry trade, [[crash risk]], negative skewness, [[funding liquidity]], risk reversals

## Idea
Equity analogue of 'after losses, insurance is pricey but crash risk is lower': go long QQQ for the next day when the 20-day return is negative and put skew is in its top 30% of the past year.

## Test
NO EDGE: 211 days, hit 51.2% (always-long 51.2%), avg -15.8 bps/day, t=-0.98, positive in 4/9 years
How: Built from same-day-close r20 and skew (skew rank over trailing 252 days); the paper's FX and TED-spread data are not in memory.

Part of [[Research engine]]