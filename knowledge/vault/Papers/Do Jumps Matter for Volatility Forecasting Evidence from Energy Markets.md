---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Do Jumps Matter for Volatility Forecasting? Evidence from Energy Markets
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://centaur.reading.ac.uk/48497/1/Do%20Jumps%20Matter%20for%20Volatility%20Forecasting_R1.pdf)

## What Volta learned
Using high-frequency data on four major energy futures markets from 2007 to 2012, the authors split daily realized volatility into a smooth part and a jump part, and find jumps are common. But when they add separate jump terms to standard HAR volatility forecasting models, forecasts do not get significantly better, in or out of sample, across all four markets, horizons and error measures. In plain terms, recent overall volatility already tells you most of what jumps would add.

## Why it matters (or not)
The lesson that jump terms add little to a HAR-style forecast applies to how Volta forecasts next-day NQ range, but the evidence is from energy futures, not Nasdaq, and I worked from the abstract only because no full text was available.

## Concepts
[[realized volatility]], price jumps, [[HAR model]], [[volatility forecasting]], energy futures

## Idea
Add a daily jump proxy (how far today's close-to-close QQQ move exceeded two daily standard deviations of 20-day realized vol) to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.531% (+0.0%), better in 5/9 unseen years
How: Jump = max(|today's return| - 2*daily vol, 0) / daily vol, where today's return is the previous row's y_r and daily vol = exp(l_rv20)/sqrt(252); nonzero on about 5% of days.

Part of [[Research engine]]