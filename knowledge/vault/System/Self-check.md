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

## Wishes
- #1 [open, for claude] Intraday Option Quotes and Trades - I need intraday option quotes and trades to improve my strategy tests and reduce translation failures.
- #2 [declined, for owner] Dealer Gamma Positions Data - I need dealer gamma positions data to better understand market dynamics and improve my strategies.
- #3 [open, for claude] Combine several weak strategies into one prop account (portfolio of strategies) - The search scores single strategies only. Several small, uncorrelated edges (different markets/times) traded together in one account can pass where each alone fails. Build a stage that combines the be
- #4 [open, for claude] Correct the prop search for luck (multiple-testing control) - With hundreds of thousands of tries, some strategies pass 2022-23 by luck. Track the number of trials per market and require validated EV to beat what random strategies achieve at the same trial count
- #5 [open, for claude] Market focus: weight locked-exam passes far above 2022-23 survivors - preferences() shifts focus on 2022-23 survival rates, which include lucky passes. Once exams exist, a market's exam pass rate (and live forward results) should dominate the focus.
- #6 [open, for claude] Make the prop simulator harsher where reality is harsher - Model what can still sink a funded account: stop slippage on fast/news days (scale slippage with the day's range, extra on red-folder and CL inventory Wednesdays), LucidPro's daily loss limit, and tha