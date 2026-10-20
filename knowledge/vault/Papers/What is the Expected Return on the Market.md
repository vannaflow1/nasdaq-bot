---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# What is the Expected Return on the Market?*
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://academic.oup.com/qje/article-pdf/132/1/367/17098108/qjw034.pdf)

## What Volta learned
Ian Martin (Quarterly Journal of Economics) shows that index option prices give a lower bound on the stock market's expected return above cash, via a volatility index he calls SVIX. The bound averages about 5% a year but swings wildly, rising above 20% at the height of the 2008 crisis, and predictive regressions do not reject the idea that it is roughly the true equity premium. He argues that the high expected returns available in stressed, high-volatility periods are concentrated over the very short run, and he also derives a market-crash probability and 'simple variance swaps' traded on SVIX.

## Why it matters (or not)
It links option-implied volatility to expected index returns, which touches QQQ direction, but it is about S&P 500 premia over months, not next-day trades, and I worked from the abstract only because no full text was available.

## Concepts
svix, equity premium lower bound, risk-neutral variance, crash probability, simple variance swaps

## Idea
Proxy SVIX with Nasdaq 30-day ATM implied vol and go long QQQ for the next day only when it is above its trailing one-year median (high option-implied premium), staying flat otherwise.

## Test
NO EDGE: 971 days, hit 56.1% (always-long 56.1%), avg +7.0 bps/day, t=1.15, positive in 7/9 years
How: Signal +1 when today's l_iv30 exceeds its rolling 252-day median (min 200 days, through today's close), else 0; a long/short version (short when below) also showed no edge (t=-0.44).

Part of [[Research engine]]