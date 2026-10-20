---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# When Does Attention Matter? The Effect of Investor Attention on Stock Market Volatility Around News Releases
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://www.sciencedirect.com/science/article/pii/S1057521922001466/pdf)

## What Volta learned
The study examines how retail and institutional investor attention affects stock market volatility around news releases for 360 S&P 500 stocks. It finds that higher retail investor attention increases post-announcement volatility, while institutional investor attention slightly decreases it. These effects vary by news type and topic.

## Why it matters (or not)
The paper provides insights into how different types of investor attention influence market volatility, which could be useful for traders, but it does not directly offer a trading strategy or model.

## Concepts
investor attention, [[stock market volatility]], news releases

## Idea
A testable trading idea could involve creating a strategy that takes into account the type of investor attention around news releases to predict stock volatility and adjust position sizes accordingly.

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.531% (+0.0%), better in 4/9 unseen years
How: feature `event_prem` added to the brain's range model
Touches: [[Brain]]

Part of [[Research engine]]