---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# The lead–lag relation between VIX futures and SPX futures
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.finmar.2023.100851)

## What Volta learned
The authors studied how VIX futures and S&P 500 futures move against each other minute by minute. When markets are calm the two are only loosely connected, but when volatility is high they move strongly in opposite directions and VIX futures tend to move first, with S&P futures following. The lead is so short that, after transaction costs, it could not be turned into a profitable strategy; whichever market is relatively more liquid tends to lead, and market-maker hedging also shapes the relation. Worked from the abstract only (no full text in the repo), so no correlation or lag figures are given.

## Why it matters (or not)
Useful intraday context that VIX moves can front-run index futures in stressed markets, but the effect is seconds-to-minutes and not tradeable after costs, and a daily version of the idea found nothing in my data.

## Concepts
lead-lag, [[vix futures]], [[volatility regimes]], [[price discovery]], market-maker hedging

## Idea
Daily vol-leads-price: on high-volatility days (20d realized vol above its trailing median), go short QQQ the next day if 30d IV rose today and long if it fell; also add today's IV change to the next-day NQ range forecast.

## Test
NO EDGE: 1041 days, hit 48.4% (always-long 55.1%), avg -8.3 bps/day, t=-1.51, positive in 2/9 years
How: Signal = -sign(today's change in l_iv30) on days where l_rv20 exceeds its expanding median up to the previous day; the range add-on (IV change, its high-vol interaction and its absolute size) was also NO EDGE (0.531% -> 0.533%, better in 1/9 years). The paper's effect is intraday, which daily closes cannot capture.

Part of [[Research engine]]