---
tags: [paper]
relevance: 2
read: 2026-11-01
---
# FOMO: FLEX Options and Market Outcomes
★★☆☆☆  ·  Frontier (arXiv, last 45 days)  ·  [source](https://arxiv.org/abs/2610.13044v1)

## What Volta learned
FLEX options are custom exchange‑traded contracts that spike in volume. The paper finds that FLEX events are followed by higher open interest in standard options, tend to occur in high‑IV stocks (especially midsized price levels), and that the IV‑minus‑realized‑vol spread on the event day predicts the return of a short‑straddle trade.

## Why it matters (or not)
The study links FLEX activity to listed‑option open interest and IV spreads, but does not provide directly usable signals for Nasdaq futures/options.

## Concepts
[[flex options]], open‑interest spillover, iv‑realized‑vol spread, volatility‑carry, event‑study did

## Idea
When a FLEX consolidation occurs for a single‑name equity, compute the day‑of‑event IV‑minus‑realized‑vol spread using our IV and realized‑vol columns; if the spread is positive, go short a 1‑day ATM straddle (sell one call and one put) and hedge with delta‑neutral position, targeting the expected positive return reported (beta ≈ 0.0366).

## Test
not testable with my data yet

Part of [[Research engine]]