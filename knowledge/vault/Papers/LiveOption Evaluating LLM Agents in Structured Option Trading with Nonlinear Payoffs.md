---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# LiveOption: Evaluating LLM Agents in Structured Option Trading with Nonlinear Payoffs
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://arxiv.org/pdf/2609.33470)

## What Volta learned
LiveOption is a test bed where six AI language-model agents traded options live in three tasks: hedging or covered-call overlays on stocks, earnings bets, and intraday 0DTE trading over 102 sessions. None beat simply holding the stock in the overlay task, every model had a negative median return on earnings bets, and in 0DTE each model lost on 62-76 of the 102 sessions with medians of -3.20% to -0.26% per session. The few positive 0DTE averages came from a handful of big winning days and turned negative once the real bid-ask half-spread was charged, mainly because agents kept paying time decay (theta) on bought options.

## Why it matters (or not)
Read the repo's full text; a useful cautionary result that buying 0DTE options without an edge bleeds theta and spread costs, but it evaluates AI agents rather than giving a market signal for NQ/QQQ.

## Concepts
llm trading agents, 0dte intraday trading, [[time decay]], bid-ask costs, benchmarking

## Idea
Score a rule-based 0DTE QQQ long-option strategy net of real half-spreads and theta.

## Test
not testable with my data yet

Part of [[Research engine]]