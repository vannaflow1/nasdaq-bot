---
tags: [paper, curated]
relevance: 4
read: 2026-10-19
---
# Generalized autoregressive conditional heteroskedasticity
★★★★☆  ·  Must-read (curated)  ·  [source](http://www.eeri.eu/documents/wp/EERI_RP_1986_01.pdf)

## What Volta learned
The paper introduces the Generalized Autoregressive Conditional Heteroskedasticity (GARCH) model, which is used to analyze and forecast volatility in financial time series. The GARCH model captures the volatility clustering phenomenon, where periods of high volatility tend to be followed by periods of high volatility, and periods of low volatility tend to be followed by periods of low volatility.

## Why it matters (or not)
This is a foundational paper in the field of financial econometrics, and its relevance to traders and quants is high due to its application in modeling and forecasting volatility.

## Concepts
[[GARCH]], [[volatility clustering]], heteroskedasticity

## Idea
Can a GARCH model be used to improve the accuracy of volatility forecasts, and subsequently, inform risk management and position sizing decisions?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: range-forecast miss 0.531% -> 0.529% (+0.4%), better in 7/9 unseen years
How: GARCH(1,1) on daily QQQ log returns (y_r shifted one day, zero mean), fitted by maximum likelihood each year on data before that year only; feature = log of the GARCH next-day volatility forecast made at today's close, added to the range model. 2014-15 rows (training only) use parameters fit on 2014-15.

Part of [[Research engine]]