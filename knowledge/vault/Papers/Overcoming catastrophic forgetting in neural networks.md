---
tags: [paper]
relevance: 4
read: 2026-10-21
---
# Overcoming catastrophic forgetting in neural networks
★★★★☆  ·  OpenAlex (about itself)  ·  [source](https://arxiv.org/pdf/1612.00796)

## What Volta learned
The paper introduces Elastic Weight Consolidation (EWC), which protects important network parameters by adding a quadratic penalty weighted by the Fisher information, allowing sequential learning without catastrophic forgetting.

## Why it matters (or not)
EWC offers a lightweight, mathematically simple way to retain past models, fitting Volta's limited resources.

## Concepts
elastic weight consolidation, fisher importance weighting, quadratic penalty, continual learning, parameter stability

## Lesson for Volta
Add an EWC‑style regularization term when fine‑tuning Volta's models on new data, using the Fisher diagonal from previous training to scale learning rates per weight.

Feeds [[Self-check]]

Read about itself - part of [[Self-check]]