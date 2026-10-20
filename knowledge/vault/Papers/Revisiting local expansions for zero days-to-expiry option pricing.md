---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Revisiting local expansions for zero days-to-expiry option pricing
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.1016/j.finr.2025.100053)

## What Volta learned
Same-day-expiry (0DTE) options are hard to price because over a few hours prices move in jumps and lopsided ways that the normal bell-curve model misses. The authors price them with a fast 'local expansion' formula that adds corrections for skew and fat tails, and find that letting jumps follow a fat-tailed (tempered stable) shape prices SPX 0DTE options clearly better than assuming bell-shaped jumps; the method also held up on DAX and Euro Stoxx 50 0DTE options. The abstract gives no specific error numbers.

## Why it matters (or not)
Worked from the abstract only (no full text available); it is a pricing-model paper that confirms 0DTE tails are fatter than a normal model implies, useful background for QQQ 0DTE traders but it gives no daily trading signal.

## Concepts
[[0DTE options]], [[jump-diffusion]], edgeworth expansion, tempered stable jumps, fat tails

## Idea
Fit fat-tailed jump models to intraday 0DTE QQQ option quotes to spot mispriced wings.

## Test
not testable with my data yet

Part of [[Research engine]]