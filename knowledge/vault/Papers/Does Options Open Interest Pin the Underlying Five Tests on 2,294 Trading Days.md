---
tags: [paper]
relevance: 4
read: 2026-10-18
---
# Does Options Open Interest Pin the Underlying? Five Tests on 2,294 Trading Days
★★★★☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.5281/zenodo.19540115)

## What Volta learned
Using 1.6 million near-expiry SPY option records matched to one-minute E-mini S&P futures over 2,294 trading days (2016-2025), the author runs five tests and finds no sign that big open interest 'pins' the index to a strike at expiry, unlike studies of the pre-2009 market. The only significant result (p < 0.001) goes the other way: days with the highest at-the-money open interest had about 16% wider daily ranges than days with the lowest. The author reads this as a shift from pinning to gamma-driven amplification, possibly tied to the growth of weekly and 0DTE options. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
Directly about index expiry-day range behavior in the modern 0DTE era, though it uses SPY/ES rather than NQ/QQQ and I have no open-interest column to replicate the 16% finding; judged from the abstract only.

## Concepts
[[strike pinning]], open interest, gamma amplification, [[0DTE options]], options expiration

## Idea
Expiry dynamics: add a flag for 'next session is the monthly options expiration (third Friday)' and that flag times dealer gamma rank to the next-day NQ range forecast.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: power 'trend_day' (base 37%): lowest-fifth days 36% vs highest-fifth 35%, Brier skill -0.3%, better than the base rate in 6/9 unseen years
How: `gex_rank * next_opex` as a predictor of 'trend_day' (next session is a trend day (body >= 60% of the range))
Touches: [[Open read (powers)]]

Part of [[Research engine]]