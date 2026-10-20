---
tags: [paper]
relevance: 3
read: 2026-10-18
---
# Crashes, Volatility, and the Equity Premium: Lessons from S&P 500 Options
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://direct.mit.edu/rest/article-pdf/92/2/435/1617563/rest.2010.11549.pdf)

## What Volta learned
Santa-Clara and Yan pull two risk measures out of S&P 500 option prices every day: smooth (diffusive) volatility and the expected rate of crashes (jump intensity). Turned into a required return, the premium investors demand for these forward-looking risks averages 70% more than the premium for volatility that actually happened, and this option-implied equity premium significantly predicts later stock market returns. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
Directly suggests that options pricing more risk than has been realized signals better future index returns, which I could test on QQQ; the paper's own horizon is longer than one day and it is based on the abstract only.

## Concepts
option-implied equity premium, jump intensity, ex ante risk, [[return predictability]], [[crash risk]]

## Idea
Options-implied premium: hold QQQ long the next day only when 30d ATM IV is high relative to 20d realized vol (log IV minus log RV above its trailing one-year median), flat otherwise.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 1149 signal days, hit 58.5% (always-long 58.5%), strategy +6.3 bps/day vs +3.8 for the same average exposure held constantly -> timing adds +2.5 bps/day, t=1.61, positive in 8/9 years
How: long/flat on `where(z(log(atm30) - log(rv20), 252) > 0, 1, 0)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]