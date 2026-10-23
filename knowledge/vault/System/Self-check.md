---
tags: [system]
---
# Self-check
Once a day Volta reviews its own state (scores, failures and their reasons, near-misses), writes a diary, queues follow-up questions/strategies it can run itself, and files wishes for what it can't do alone - for Claude (research-side code/data, granted in the Sunday session) or for the owner (his data, money, accounts, live decisions).

- [[Research engine]]
- [[Strategy lab]]
- [[Questions Volta asked]]

## Diary
- 2026-10-20: This week, I tested 88 ideas, but none showed consistent promise. My near-miss features like garch, next_opex, and log(impl) * rank(iv30, 252) showed slight improvements. However, my strategies still struggle, with only 0 passing out of 37 tested. I need to focus on improving my translation process and data quality.
- 2026-10-21: I realized my range forecasts are mathematically solid (3% avg miss, 100% coverage) but they never translate into profitable trades because my intraday edge ideas still lack sufficient edge. Near‑miss features (garch, next_opex, log(impl)*rank(iv30,252)) give tiny lifts but I haven’t proven they survive multiple‑testing correction. Also, my strategy lab shows zero passed specs, suggesting my filters are too blunt. Next I will directly test whether low‑dealer‑gamma days truly forecast larger next‑day NQ moves using the columns I already have, and I will prototype a hybrid strategy that blends the modestly positive “LowGammaFadeOnHigh” edge with the “Gap‑fill toward yesterday’s close” edge under a tighter filter.
- 2026-10-22: I see that my range forecasts are reliable but I still struggle to turn them into profitable trades. Near‑miss features linked to low dealer gamma (gex_rank) keep nudging performance up by ~0.2%, yet I have never built a dedicated low‑gamma regime strategy. My backtests also show that simple break‑out ideas give tiny R, so I need a higher‑probability edge that exploits the proven low‑gamma → bigger next‑day moves relationship.
- 2026-10-23: I confirmed that low‑dealer‑gamma days (gex_rank<0.2) consistently give a modest +0.2% edge on my near‑miss features, but I still haven’t turned that into a robust intraday profit. My best in‑sample breakout idea (first 15‑min up move) barely beats break‑even and only works on a subset of sessions. I need to fuse the low‑gamma signal with a more disciplined entry/exit framework and test it across both NQ and ES to increase trade count.

## Wishes
- #1 [done, for claude] Intraday Option Quotes and Trades - I need intraday option quotes and trades to improve my strategy tests and reduce translation failures.
- #2 [declined, for owner] Dealer Gamma Positions Data - I need dealer gamma positions data to better understand market dynamics and improve my strategies.
- #3 [done, for claude] Combine several weak strategies into one prop account (portfolio of strategies) - The search scores single strategies only. Several small, uncorrelated edges (different markets/times) traded together in one account can pass where each alone fails. Build a stage that combines the be
- #4 [done, for claude] Correct the prop search for luck (multiple-testing control) - With hundreds of thousands of tries, some strategies pass 2022-23 by luck. Track the number of trials per market and require validated EV to beat what random strategies achieve at the same trial count
- #5 [done, for claude] Market focus: weight locked-exam passes far above 2022-23 survivors - preferences() shifts focus on 2022-23 survival rates, which include lucky passes. Once exams exist, a market's exam pass rate (and live forward results) should dominate the focus.
- #6 [done, for claude] Make the prop simulator harsher where reality is harsher - Model what can still sink a funded account: stop slippage on fast/news days (scale slippage with the day's range, extra on red-folder and CL inventory Wednesdays), LucidPro's daily loss limit, and tha
- #7 [merged, for claude] Implement robust multiple‑testing correction in the prop‑simulator - Currently 114 ideas are tested weekly; without FDR control many marginal edges look promising by chance, inflating false confidence.
- #8 [declined, for claude] Add a GARCH‑RNN hybrid volatility model as an optional feature for the brain - Near‑miss garch feature gave +0.4% in backtests, but I lack a clean, out‑of‑sample‑validated implementation to compare against the plain ridge model.
- #9 [open, for claude] Add real‑time GEX rank to live data feed - My strategies and filters rely on gex_rank but currently I only have it in backtest; a live column would let me deploy low‑gamma tactics in real time.
- #10 [open, for claude] Real‑time GEX rank feed for live strategy - All my promising low‑gamma ideas stall without live gex_rank; a low‑latency feed would let me trigger entries exactly when dealer gamma drops below 0.2.
- #11 [open, for claude] Dynamic position sizing based on consecutive profit days - Literature suggests scaling size after streaks improves long‑run EV while preserving drawdown limits; implementing this could turn modest per‑trade edges into higher overall EV.