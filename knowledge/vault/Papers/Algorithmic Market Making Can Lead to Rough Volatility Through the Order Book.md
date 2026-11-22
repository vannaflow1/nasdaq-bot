---
tags: [paper]
relevance: 3
read: 2026-11-22
---
# Algorithmic Market Making Can Lead to Rough Volatility Through the Order Book
★★★☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2611.24028v1)

## What Volta learned
The paper shows that algorithmic market‑making desks, each updating order distances by a gradient rule whenever they receive new information, generate order‑book volume dynamics that follow a stochastic PDE. The asynchronous updates across desks with different information horizons create power‑law memory in order flow, which can produce rough (sub‑Brownian) volatility in prices.

## Why it matters (or not)
The work explains a mechanism for rough volatility that could inform models of volatility dynamics, but it does not provide direct trading signals.

## Concepts
algorithmic market making, stochastic gradient descent, dean–kawasaki equation, power‑law memory in order flow, [[rough volatility]]

## Idea
Test whether days with higher dealer gamma rank (gex_rank) are associated with a lower estimated Hurst exponent of realized volatility, indicating rougher volatility when market‑making pressure is high.

## Test
queued for testing

Part of [[Research engine]]