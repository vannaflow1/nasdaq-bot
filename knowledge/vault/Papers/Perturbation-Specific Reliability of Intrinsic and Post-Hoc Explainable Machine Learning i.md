---
tags: [paper]
relevance: 2
read: 2026-11-21
---
# Perturbation-Specific Reliability of Intrinsic and Post-Hoc Explainable Machine Learning in Volatility Forecasting
★★☆☆☆  ·  OpenAlex  ·  [source](https://www.researchsquare.com/article/rs-11158626/latest.pdf)

## What Volta learned
The study finds that classic HAR-RV and spline‑based GAM models give the most accurate 5‑day realized volatility forecasts, while explainability of complex ML models (LSTM, TabNet, XGBoost) varies a lot depending on the perturbation and the explainer used.

## Why it matters (or not)
Mostly about model interpretability rather than actionable trading signals, but shows simple volatility models still dominate.

## Concepts
har‑rv, generalized additive model, intrinsic vs post‑hoc xai, explanation stability, [[walk‑forward validation]]

## Idea
Compare daily 5‑day‑ahead realized volatility forecasts from a HAR‑RV model and a spline‑based GAM on the Volta data; if GAM consistently outperforms HAR, use GAM forecasts to size option positions (e.g., adjust gamma‑ratio exposure).

## Test
not testable with my data yet

Part of [[Research engine]]