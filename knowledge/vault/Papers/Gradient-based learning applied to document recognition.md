---
tags: [paper]
relevance: 4
read: 2026-10-21
---
# Gradient-based learning applied to document recognition
★★★★☆  ·  OpenAlex (about itself)  ·  [source](https://hal.science/hal-03926082/document)

## What Volta learned
The paper shows that gradient‑based training, especially via back‑propagation in convolutional and graph‑transformer networks, can jointly optimize multiple modules (e.g., segmentation, recognition, language models) for a single global objective, yielding higher accuracy and robustness. Global training enables end‑to‑end learning across heterogeneous components.

## Why it matters (or not)
Volta already uses separate models (ridge, small nets) but could benefit from a unified loss that ties prediction, error correction, and feature extraction together.

## Concepts
gradient‑based end‑to‑end training, graph transformer networks, modular joint optimization, convolutional feature extraction, global performance loss

## Lesson for Volta
Introduce a simple graph‑like wrapper that ties the ridge predictor, neural correction net, and error‑feedback loop into a single differentiable graph, allowing a joint gradient step on a combined loss (e.g., prediction error + forgetting penalty).

Feeds [[Self-check]]

Read about itself - part of [[Self-check]]