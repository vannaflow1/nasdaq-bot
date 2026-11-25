---
tags: [paper]
relevance: 2
read: 2026-11-25
---
# Equilibria and Learning in Competitive Market Making
★★☆☆☆  ·  arXiv  ·  [source](https://arxiv.org/abs/2610.30891v1)

## What Volta learned
The paper proves that in a market with several competing makers, a pure‑strategy Nash equilibrium always exists and that the equilibrium bid‑ask spread grows linearly with the underlying asset’s volatility, even without collusion or informed traders.

## Why it matters (or not)
The result is theoretical and not directly tied to a concrete trading rule, but it suggests a simple link between volatility and optimal spread.

## Concepts
nash equilibrium, competitive spread widening, volatility‑scaled spread, no‑regret learning, tick‑size limit

## Idea
Set the bid‑ask spread each day to a constant multiple of the asset’s realized volatility (e.g., spread = k * σ20), and test whether this rule improves execution cost versus a static spread.

## Test
not testable with my data yet

Part of [[Research engine]]