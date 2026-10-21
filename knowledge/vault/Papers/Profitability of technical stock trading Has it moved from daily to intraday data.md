---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Profitability of technical stock trading: Has it moved from daily to intraday data?
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.econstor.eu/bitstream/10419/128874/1/wp_323.pdf)

## What Volta learned
Stephan Schulmeister (WIFO, 2008) ran 2,580 moving-average and momentum trading rules on the S&P 500. On daily prices their average yearly gross return fell from 8.6% (1960-71) to about zero in 1983-91 and -5.1% in 1992-2000, so daily chart rules stopped working. The same rules on 30-minute S&P futures prices still made about 7.2% a year gross from 1983 to 2007 (contrarian rules 9.1%, trend rules 4.8%), with roughly 0.01% cost per trade assumed, though results weakened in 2001-07.

## Why it matters (or not)
Relevant as a caution for index day-traders (simple daily chart rules on US index futures have been dead since the 1990s, edge moved intraday and was fading by 2007), but the data ends in 2007 and my memory cannot test 30-minute rules.

## Concepts
[[technical trading rules]], moving averages, intraday momentum and reversal, s&p 500 futures, declining profitability

## Idea
Check the paper's daily-data claim on QQQ: follow the 20-day trend (long if the last 20 days were up, short if down) for the next day.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2227 signal days, hit 53.1% (always-long 56.5%), strategy +4.5 bps/day vs +2.8 for the same average exposure held constantly -> timing adds +1.7 bps/day, t=0.49, positive in 5/10 years
How: long/short on `r20` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]