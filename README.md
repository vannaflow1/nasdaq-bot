# nasdaq-bot

Daily Nasdaq briefing bot, running entirely on GitHub Actions (no PC needed).

| Workflow | When (Luxembourg time) | What |
|---|---|---|
| `morning` | weekdays ~14:45 | risk level + what to do, expected range, gamma walls, today's events, overnight Trump posts & news |
| `evening` | weekdays ~22:40 | QQQ dealer gamma (validated), tomorrow's risk & range, NDX gamma log, events, earnings moves, news, forecast grading, Friday recap |
| `trump` | every 5 min | new market-relevant Truth Social posts, pushed instantly |
| `manual` | on demand | run any mode by hand (`test` checks every data source) |
| `register-discord` | once | registers Volta's slash commands |

Notifications go to ntfy (topic stored as the `NTFY_TOPIC` secret). Discord slash commands are answered by a
Cloudflare Worker (`worker/worker.js`) that reads `status.json` from this repo.

State lives in the CSV/JSON files and is committed back after every run.
Not financial advice - the only validated signal is "dealer gamma predicts the SIZE of tomorrow's moves".
