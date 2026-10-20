---
tags: [paper]
relevance: 2
read: 2026-10-19
---
# Short-Sale Strategies and Return Predictability
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://scholarsarchive.byu.edu/cgi/viewcontent.cgi?article=10102&context=facpub)

## What Volta learned
Using SEC-mandated short-sale data for US stocks in 2005, the authors find short selling is huge: 24% of NYSE and 31% of Nasdaq share volume. Short sellers step up their selling after a stock has risen, and those stocks then go on to underperform, so a strategy following daily short-selling activity earned significant positive returns in that year. Their reading is that short sellers bet against short-term overreaction. I worked from the abstract only because no full text was available.

## Why it matters (or not)
The overreaction idea is relevant to next-day QQQ direction, but the evidence is single-stock short-sale flow in one year (2005), which I do not have, and I only had the abstract.

## Concepts
short selling, [[return predictability]], short-term overreaction, regulation sho data, [[informed trading]]

## Idea
Index version of 'short sellers fade strong up days': go short QQQ for the next day only when today's QQQ return is in the top 10% of its past year, flat otherwise.

## Test
NO EDGE: 238 days, hit 49.2% (always-long 50.8%), avg +12.5 bps/day, t=1.15, positive in 5/9 years
How: Today's return = previous row's y_r (close-to-close return ending at today's close); threshold = trailing 252-day 90th percentile (min 126 days) including today; no short-sale data, so this only proxies the overreaction story.

Part of [[Research engine]]