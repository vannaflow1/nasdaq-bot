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
- 0.5*mean(rng,5) + 0.3*mean(rng5,5) + 0.2*mean(rng20,5) (+0.1%, 7/9 years) - Forecasting cryptocurrencies volatility using statistical and machine learning methods: A comparative study
- 0.5*lag(rng,1) + 0.3*lag(rng5,1) + 0.2*lag(rng20,1) (+0.1%, 6/9 years) - Measuring and Forecasting Volatility in Chinese Stock Market Using HAR-CJ-M Model
- 0.5*ewm(rng,10) + 0.3*ewm(rng5,10) + 0.2*ewm(rng20,10) (+0.1%, 7/9 years) - Range-Based Volatility Estimation and Forecasting

Last combined test (2026-10-27): NOT CONFIRMED - the combination does not hold on unseen years (picked +1.76%, unseen years -0.46%)