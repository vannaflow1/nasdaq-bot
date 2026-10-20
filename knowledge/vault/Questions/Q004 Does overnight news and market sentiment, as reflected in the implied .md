---
tags: [question, curiosity]
asked: 2026-10-20
---
# Does overnight news and market sentiment, as reflected in the implied move (impl) and event premium (event_prem), impact the likelihood of the market taking out the overnight high (y_took_overnight_high) or low (y_took_overnight_low)?
Volta asked this itself. Inspired by: Volta's own question (inspired by: The Control Layer Behind Rule-Following Agents Trading Acros; Alternative data and sentiment analysis: Prospecting 

Answer formula: `y_took_overnight_high or y_took_overnight_low`
Predictor: `impl * event_prem`

[[NOT CONFIRMED]] - NOT CONFIRMED on my data: FACT: happens on 96% of 2948 sessions (2014-19: 97%, 2020-25: 96%). Predictor: lowest-fifth days 96% vs highest-fifth 95%, skill -0.4% vs the base rate, better in 4/9 unseen years

Part of [[Questions Volta asked]]