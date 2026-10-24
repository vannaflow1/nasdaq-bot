---
tags: [paper]
relevance: 2
read: 2026-10-21
---
# A Hybrid HAR-LSTM-GARCH Model for Forecasting Volatility in Energy Markets
★★☆☆☆  ·  Frontier (rising, < 18 months old)  ·  [source](https://www.mdpi.com/1911-8074/19/1/77/pdf?version=1768646705)

## What Volta learned
A hybrid model that first fits a HAR to capture multi‑scale volatility, then feeds the HAR residuals into an LSTM to learn non‑linear patterns, and finally models the LSTM residuals with a GARCH, can improve daily realized‑volatility forecasts over pure HAR, GARCH(1,1) or LSTM alone.

## Why it matters (or not)
The paper deals with energy‑future volatility, not directly Nasdaq/S&P, but the hybrid approach could be adapted to equity index volatility forecasts.

## Concepts
har volatility model, [[lstm neural network]], garch residual modeling, hybrid forecasting, [[realized volatility]]

## Idea
Build a HAR‑LSTM‑GARCH pipeline on the daily log‑realized volatility column (l_rv20) for the Nasdaq futures, using the HAR component on 1‑day, 5‑day, 20‑day lagged volatility, an LSTM on the HAR residuals, and a GARCH(1,1) on the LSTM residuals; then evaluate forecast RMSE versus a plain HAR and a plain GARCH.

## Test
not testable with my data yet

Part of [[Research engine]]