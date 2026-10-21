---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# Measuring and Forecasting Volatility in Chinese Stock Market Using HAR-CJ-M Model
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://downloads.hindawi.com/journals/aaa/2013/143194.pdf)

## What Volta learned
The paper introduces the HAR-CJ-M model, an extension of the HAR-CJ model, which incorporates momentum effect and adjusted realized volatility (ARV) to forecast volatility in the Chinese stock market. The HAR-CJ-M model outperforms HAR-ARV and HAR-CJ models in forecasting future volatility. The study finds that continuous sample path variation, momentum effect, and ARV have good forecasting performance, while discontinuous jump variation has poor performance.

## Why it matters (or not)
The paper is related to volatility modeling, but its focus on the Chinese stock market and specific models (HAR-CJ-M, HAR-ARV, HAR-CJ) limits its direct applicability to Nasdaq/S&P index futures and options trading.

## Concepts
har-cj-m model, [[volatility forecasting]], [[realized volatility]]

## Idea
Can the HAR-CJ-M model's performance be replicated in Nasdaq/S&P index futures and options using daily realized volatility and momentum effect data?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.531% (+0.1%), better in 6/9 unseen years
How: feature `0.5*lag(rng,1) + 0.3*lag(rng5,1) + 0.2*lag(rng20,1)` added to the brain's range model
Touches: [[Brain]]
In the [[Near-miss pool]] - re-tested together with the others monthly.

Part of [[Research engine]]