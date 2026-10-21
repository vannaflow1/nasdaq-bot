---
tags: [paper]
relevance: 3
read: 2026-10-20
---
# HYBRID FUZZY NEURAL NETWORK TO PREDICT PRICE DIRECTION IN THE GERMAN DAX-30 INDEX
★★★☆☆  ·  OpenAlex (classic)  ·  [source](https://journals.vgtu.lt/index.php/TEDE/article/download/6394/5541)

## What Volta learned
The paper proposes a hybrid fuzzy neural network (HyFIS) to predict the one-day ahead direction of the German DAX-30 stock index. The model uses technical indicators and oscillators as inputs, and the results show that reducing the dimensionality of the inputs through factor analysis generates more profitable and less risky strategies.

## Why it matters (or not)
The paper is related to machine learning and predictive modeling, but it focuses on the German DAX-30 index and uses a specific type of neural network, which may not be directly applicable to Nasdaq/S&P index futures and options.

## Concepts
hybrid fuzzy neural network, [[technical indicators]], factor analysis, predictive modeling

## Idea
Can a hybrid fuzzy neural network predict the direction of the Nasdaq/S&P index using technical indicators and oscillators as inputs?

## Test
[[NOT CONFIRMED]] - NOT CONFIRMED on my data: 2223 signal days, hit 46.6% (always-long 56.5%), strategy -5.7 bps/day vs -3.6 for the same average exposure held constantly -> timing adds -2.1 bps/day, t=-0.82, positive in 4/10 years
How: long/short on `sign(r20) * (rank(iv30, 126) - 0.5)` (positive = signal on)
Touches: [[Options nerd]]

Part of [[Research engine]]