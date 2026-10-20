---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Temporal Obfuscation Testing for LLM Structural Reasoning: From Single-Day Dealer Constraints to Persistent Market Regimes
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.3390/jrfm19060382)

## What Volta learned
The paper is mainly about checking whether a large language model really reasons or just remembers: it strips dates and tickers from dealer gamma exposure (GEX) data and asks the model to spot hedging patterns from the numbers alone, over 2,221 evaluations from 2020-2025. It reports 91.2% predictive accuracy on single-day patterns, and that raw strike-level data beat pre-computed GEX numbers by 30.8 points (92.3% vs 61.5%). For multi-day regimes, detection rose from 3.7% in 2021 to 100% in 2024 alongside 0DTE growth and GEX size growing from $3.0B to $20.3B, while the related strategy's Sharpe fell from 1.8 to 0.1, which the author reads as a real structure that is no longer profitable. Worked from the abstract only (no full text in the repo).

## Why it matters (or not)
Mostly a method for testing AI models; the market takeaways (strike-level beats summary GEX, the gamma edge's Sharpe collapsing to 0.1) are interesting but rest on an LLM-detection setup, not a trading test I can reproduce; abstract only.

## Concepts
temporal obfuscation, llm validation, gamma exposure regimes, 0dte adoption, strike-level data

## Idea
The paper's signal needs strike-level gamma data and an LLM classifier; my memory only has a single summary gamma rank, which the paper itself says loses much of the signal.

## Test
not testable with my data yet

Part of [[Research engine]]