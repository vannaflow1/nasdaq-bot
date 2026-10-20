---
tags: [paper]
relevance: 0
read: 2026-10-18
---
# Decomposing the Theta Cliff: A SIMDEC Filtering of Asymptotic Time-Decay in Long-Call Options with a Real-Money Intraday Illustration
☆☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.mdpi.com/2673-2688/7/7/257/pdf?version=1783853566)

## What Volta learned
This paper proposes scaling the normal Black-Scholes theta (time decay) by a factor that depends on the stock's sector and market regime, found with a sensitivity-analysis method called SIMDEC. Its main 'evidence' is three real-money long-call positions tracked through eleven intraday snapshots plus output from the author's own AI pipeline. There are no clear performance numbers, and the sample is far too small to show that the adjusted theta predicts anything.

## Why it matters (or not)
A three-trade anecdote and claims of being 'hallucination free' are not evidence; nothing here is usable for NQ/QQQ decisions.

## Concepts
theta decay, effective theta, simdec decomposition, long calls

## Idea
Scale theta by a sector/regime factor and check if long-call decay is mis-estimated.

## Test
not testable with my data yet

Part of [[Research engine]]