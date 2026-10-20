---
tags: [paper]
relevance: 2
read: 2026-10-18
---
# Central Bank Participation in Currency Options Markets
★★☆☆☆  ·  OpenAlex (classic)  ·  [source](https://www.elibrary.imf.org/downloadpdf/view/journals/001/1999/140/001.1999.issue-140-en.pdf)

## What Volta learned
The paper asks whether a central bank can calm an exchange rate by trading currency options instead of buying and selling the currency itself. Its key point is that if the central bank sells options, market makers end up long those options and their delta-hedging pushes against price moves (they sell rallies and buy dips), which dampens volatility; selling a strangle can also make a target zone more credible and may cost less than spot intervention, but it exposes the bank to unlimited losses. Worked from the abstract only (no full text in the repo), so no cost or volatility figures are given.

## Why it matters (or not)
The mechanism (dealers long options hedge in a stabilizing way) is the same logic behind dealer-gamma readings for QQQ, which the brain already uses, but the paper is about FX policy and adding extreme-gamma effects found nothing new.

## Concepts
dealer long gamma, dynamic delta hedging, short strangle, target zone, fx intervention

## Idea
Stabilizing dealer hedging: test whether the effect of dealer gamma on the next-day NQ range is non-linear, by adding flags for very high (top 20%) and very low (bottom 20%) gamma rank plus its square.

## Test
NO EDGE: range-forecast miss 0.531% -> 0.534% (-0.5%), better in 5/9 unseen years
How: Built from today's gex_rank (known at the close): its square, a flag for gex_rank > 0.8 and a flag for gex_rank < 0.2; the linear gex_rank is already in the brain's base model.

Part of [[Research engine]]