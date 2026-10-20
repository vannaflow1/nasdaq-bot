---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Asymmetric Dynamics in the Correlations of Global Equity and Bond Returns
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](http://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp204.pdf)

## What Volta learned
Cappiello, Engle and Sheppard modelled how volatility and correlations of national stock and government bond indexes change over time, using 15 years of weekly returns (790 weeks, January 1987 to February 2001) and an asymmetric correlation model. Stock indexes get more volatile after bad news than after good news of the same size, while bond volatility shows little such asymmetry; yet both stocks and bonds become more correlated with each other after joint bad news, with stocks reacting more strongly, so diversification shrinks exactly when markets fall. After the euro's launch in January 1999 correlations jumped (bond returns inside the euro area became nearly perfectly correlated) while volatility levels did not break. The repo text was glyph-encoded and was decoded for reading.

## Why it matters (or not)
Confirms that equity volatility reacts more to down moves and that correlations rise in sell-offs, which matters for hedging, but it uses weekly international data and a daily asymmetric add-on made my next-day NQ range forecast worse.

## Concepts
asymmetric volatility, [[dynamic conditional correlation]], correlation in downturns, [[stock-bond correlation]], [[structural break]]

## Idea
Asymmetric volatility response: add today's squared negative QQQ return and squared positive QQQ return as separate inputs to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.541% (-1.9%), better in 3/9 unseen years
How: Today's QQQ return taken as the previous row's y_r (the return realised by today's close); inputs are its negative part squared and positive part squared (x1e4). The correlation findings could not be tested because memory has no bond or cross-market data.

Part of [[Research engine]]