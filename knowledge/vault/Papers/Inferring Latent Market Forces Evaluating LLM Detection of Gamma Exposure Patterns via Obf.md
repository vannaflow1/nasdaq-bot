---
tags: [paper]
relevance: 1
read: 2026-10-19
---
# Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2512.17923)

## What Volta learned
Regan and Xie fed an AI language model end-of-day SPY dealer-gamma numbers for 242 trading days of 2024, with dates and tickers hidden, and asked whether it saw dealer-hedging patterns; it flagged one 71.5% of the time (100% when given hints), and they say 91.2% of flags 'materialized'. But by their own concrete test (next-day move above 0.3% or intraday range above 1%) only 41.6% materialized, every single day in the sample was classed as negative gamma, and gamma only weakly predicted volatility two days later (p=0.042 at lag 2, not significant at lags 1, 3, 4, 5). Net profit after costs faded from +16 bps in Q1 to 0 by Q4.

## Why it matters (or not)
Mostly about testing an AI's reasoning, with loose success criteria, one year of SPY and no gamma variation in the sample, so it adds little for NQ/QQQ trading; the one concrete claim (gamma predicts volatility 2 days later) did not hold in my memory. (A duplicate queue entry of the same paper, openalex:W7117127131, was removed too.)

## Concepts
[[dealer gamma]], dealer hedging, llm pattern detection, obfuscation testing, granger causality

## Idea
Paper claims dealer gamma predicts realized volatility with a 2-day lag: add yesterday's and the day before's dealer gamma rank as features to the next-day NQ range forecast.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.532% (-0.1%), better in 2/9 unseen years
How: gex_rank shifted by 1 and 2 market days (known at today's close); a 'gamma rank below 0.2' threshold flag (the paper's 'presence not size' claim) was also NO EDGE: 0.531% -> 0.534%, better in 5/9 years.

Part of [[Research engine]]