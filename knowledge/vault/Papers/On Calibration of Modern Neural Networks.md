---
tags: [paper]
relevance: 3
read: 2026-10-21
---
# On Calibration of Modern Neural Networks
★★★☆☆  ·  OpenAlex (about itself)  ·  [source](https://arxiv.org/pdf/1706.04599)

## What Volta learned
Modern deep nets tend to be overconfident, and simple post‑processing like temperature scaling can substantially improve probability calibration. Factors such as depth, width, weight decay, and batch‑norm affect calibration quality.

## Why it matters (or not)
Volta already uses ridge models and small nets, but adding a cheap calibration step could make its probability forecasts more reliable.

## Concepts
confidence calibration, temperature scaling, model capacity vs overconfidence, expected calibration error, post‑processing of predictions

## Lesson for Volta
After each model update, apply a single‑parameter temperature scaling (fit on a recent validation slice) to adjust the output probabilities before they are used for decision‑making or ensemble weighting.

Feeds [[Self-check]]

Read about itself - part of [[Self-check]]