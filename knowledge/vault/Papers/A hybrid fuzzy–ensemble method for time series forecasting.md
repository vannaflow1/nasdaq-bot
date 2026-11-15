---
tags: [paper]
relevance: 2
read: 2026-11-15
---
# A hybrid fuzzy–ensemble method for time series forecasting
★★☆☆☆  ·  Hunt: temperature scaling ensemble forecasts financial time series  ·  [source](https://doi.org/10.1038/s41598-026-51585-w)

## What Volta learned
The paper proposes a rule-free forecasting system that first clusters lagged versions of a univariate series with fuzzy c‑means, then trains a separate random‑forest regressor for each fuzzy cluster and combines their predictions weighted by membership degrees. Hyper‑parameters are jointly tuned via random search.

## Why it matters (or not)
The method is a generic time‑series forecasting technique; it could be tried on our daily options‑related series but provides no direct market‑specific insight.

## Concepts
fuzzy c‑means clustering, cluster‑specific random forest, membership‑weighted aggregation, lagged representation, hyper‑parameter random search

## Idea
Create lagged features of a target variable (e.g., next‑day NQ range y_rng), apply fuzzy c‑means to partition the feature space, train a random‑forest for each fuzzy cluster, and forecast y_rng as the membership‑weighted average of the forest predictions; compare MAE/MSE against a single random‑forest baseline.

## Test
not testable with my data yet

Part of [[Research engine]]