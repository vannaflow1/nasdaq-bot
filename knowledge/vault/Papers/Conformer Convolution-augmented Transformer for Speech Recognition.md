---
tags: [paper]
relevance: 4
read: 2026-10-21
---
# Conformer: Convolution-augmented Transformer for Speech Recognition
★★★★☆  ·  OpenAlex (about itself)  ·  [source](https://arxiv.org/pdf/2005.08100)

## What Volta learned
The Conformer architecture mixes self‑attention for global context with convolutional modules for local patterns, using a macaron‑style sandwich of feed‑forward layers and pre‑norm residual connections to stay parameter‑efficient.

## Why it matters (or not)
Volta can gain robustness and efficiency by adding lightweight convolutional blocks to its attention‑based predictors.

## Concepts
self‑attention + convolution fusion, macaron feed‑forward sandwich, pre‑norm residuals, relative positional encoding, depth‑wise gated convolutions

## Lesson for Volta
Insert a small gated depth‑wise convolution module after each attention layer in Volta's ridge‑plus‑neural‑net ensemble, using half‑step feed‑forward residuals to capture local price dynamics without blowing up model size.

Feeds [[Self-check]]

Read about itself - part of [[Self-check]]