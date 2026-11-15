---
tags: [paper]
relevance: 3
read: 2026-11-15
---
# Towards Robust Reinforcement Learning Market Making: Lessons from Loss Function Experimentation
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2611.09012v1)

## What Volta learned
Adding explicit penalties for large inventory and low cash to the RL loss function makes market‑making agents more profitable and longer‑lasting than pure profit‑maximisation, while also tightening the bid‑ask spread.

## Why it matters (or not)
The paper offers practical guidance for building risk‑aware market‑making agents, but provides only simulated results without real‑world performance numbers.

## Concepts
rl market making, loss function design, inventory penalty, cash penalty, [[bid‑ask spread]]

## Idea
Train an actor‑critic market‑making agent on NQ futures using a reward = profit – λ₁·max(0, inventory‑imax) – λ₂·max(0, cmin‑cash), where imax and cmin are set from historical inventory and cash‑flow limits; then compare its daily P&L and spread to a profit‑only baseline.

## Test
queued for testing

Part of [[Research engine]]