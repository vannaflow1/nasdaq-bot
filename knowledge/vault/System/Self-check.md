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

## Wishes
- #1 [done, for claude] Intraday Option Quotes and Trades - I need intraday option quotes and trades to improve my strategy tests and reduce translation failures.
- #2 [declined, for owner] Dealer Gamma Positions Data - I need dealer gamma positions data to better understand market dynamics and improve my strategies.
- #3 [done, for claude] Combine several weak strategies into one prop account (portfolio of strategies) - The search scores single strategies only. Several small, uncorrelated edges (different markets/times) traded together in one account can pass where each alone fails. Build a stage that combines the be
- #4 [done, for claude] Correct the prop search for luck (multiple-testing control) - With hundreds of thousands of tries, some strategies pass 2022-23 by luck. Track the number of trials per market and require validated EV to beat what random strategies achieve at the same trial count
- #5 [done, for claude] Market focus: weight locked-exam passes far above 2022-23 survivors - preferences() shifts focus on 2022-23 survival rates, which include lucky passes. Once exams exist, a market's exam pass rate (and live forward results) should dominate the focus.
- #6 [open, for claude] Make the prop simulator harsher where reality is harsher - Model what can still sink a funded account: stop slippage on fast/news days (scale slippage with the day's range, extra on red-folder and CL inventory Wednesdays), LucidPro's daily loss limit, and tha
- #7 [merged, for claude] Implement robust multiple‑testing correction in the prop‑simulator - Currently 114 ideas are tested weekly; without FDR control many marginal edges look promising by chance, inflating false confidence.
- #8 [declined, for claude] Add a GARCH‑RNN hybrid volatility model as an optional feature for the brain - Near‑miss garch feature gave +0.4% in backtests, but I lack a clean, out‑of‑sample‑validated implementation to compare against the plain ridge model.