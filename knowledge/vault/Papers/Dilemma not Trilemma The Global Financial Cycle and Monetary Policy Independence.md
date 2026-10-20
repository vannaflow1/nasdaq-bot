---
tags: [paper]
relevance: 1
read: 2026-10-18
---
# Dilemma not Trilemma: The Global Financial Cycle and Monetary Policy Independence
★☆☆☆☆  ·  OpenAlex (classic)  ·  [source](https://doi.org/10.3386/w21162)

## What Volta learned
Rey shows there is one global financial cycle: capital flows, credit growth, bank leverage and risky asset prices around the world rise and fall together, and the cycle moves opposite to the VIX (low VIX = money pours in, high VIX = flows collapse). A single global factor explains about 25% of the variation in returns across 858 risky assets worldwide, and in her quarterly VAR a cut in the Fed funds rate is followed by a lower VIX after about 5 quarters and more credit flows after about 12 quarters; other studies she cites find Fed rate shocks explain roughly 20-30% of VIX variation at horizons beyond 7-10 quarters. Her policy conclusion is that with free capital flows, countries lose monetary independence even with floating exchange rates unless they manage capital flows or use macroprudential limits on leverage.

## Why it matters (or not)
Good macro background on why the VIX regime and Fed policy drive risk assets over quarters and years, but it says nothing usable about next-day NQ moves, and my daily test only rediscovered the market's normal upward drift.

## Concepts
global financial cycle, vix as risk appetite, [[capital flows]], bank leverage, fed policy spillovers

## Idea
Low-VIX regime = risk-on: hold QQQ long the next day only when 30d IV is below its trailing one-year average, flat otherwise.

## Test
NO EDGE: 1215 signal days, hit 56.9% (always-long 56.9%), strategy +4.3 bps/day vs +4.1 for the same average exposure held constantly -> timing adds +0.2 bps/day, t=0.13, positive in 5/9 years [re-tested 19 Oct with drift-corrected test]
How: Signal = 1 when today's l_iv30 is below its 252-day rolling mean (ending today), else 0. CAUTION, not a real edge: simply always being long earned +7.4 bps/day (t=2.44) over the same period and longs on the high-IV days earned +7.0 bps/day, and the hit rate equals the always-long rate, so the verdict reflects QQQ's upward drift rather than timing skill; the long/short version (short when IV is above average) was NO EDGE (+1.1 bps/day, t=0.36).

Part of [[Research engine]]