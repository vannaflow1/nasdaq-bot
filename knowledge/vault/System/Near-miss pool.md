---
tags: [system]
---
# Near-miss pool
Ideas that helped the range forecast a little and fairly consistently. Re-tested TOGETHER every month: best mix picked on older years, judged on the last 3 unseen years.

- [[Brain]]

## Members
- garch (+0.4%, 7/9 years) - GARCH (Bollerslev) - via 'Can a GARCH model improve volatility forecasts'
- next_opex (+0.2%, 7/9 years) - Expiry dynamics: monthly options expiration next session
- log(impl) * rank(iv30, 252) (+0.2%, 3/8 years) - Volatility regime: options-implied move weighted by the IV regime
- where(gex_rank < 0.2, 1, 0) (+0.2%, 4/9 years) - Negative gamma hurts most under stress
- clip(r20, -1, 0) (+0.2%, 3/9 years) - Countercyclical volatility (recent drawdown)