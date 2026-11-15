# SIM execution path (NinjaTrader 8) - DRAFT

**Status: draft, never compiled, never run.** It was written on 15 Nov 2026 without access to NinjaTrader, from the
exact rules Volta's backtest uses. Treat the first import as a debugging session, not as a launch.
**SIM account only. Never the funded account** (frozen eval rule: "never on the manually traded funded account").

## Why this exists

Volta's frozen eval rule (`knowledge/frozen/eval_rule.json`) says no evaluation may be started before
1. the automated order path ran in a SIM account for at least 20 sessions, with fills within 0.05R per trade of Volta's
   own simulation, and
2. there are at least 60 clean forward trades.

Until 15 Nov nothing existed for point 1. This folder is the first attempt: a NinjaTrader strategy that places the same
trades Volta's forward test simulates. It does not make the edge bigger. At the current belief (+0.03R per trade) an
account is worth roughly $30 a month, so this is about being ready and learning, not about income.

## What you need

- A Windows PC with NinjaTrader 8 (free for SIM) that is on and connected from 15:30 to 22:00 Luxembourg time on
  trading days (one hour earlier, 14:30 to 21:00, in the weeks the US and Europe clocks differ).
- A data connection that gives MNQ 1-minute bars (the SIM/demo feed is enough to start).
- Nothing paid. No card.

## Steps

1. NinjaTrader: `New > NinjaScript Editor`, right-click `Strategies > New Strategy`, name it `VoltaBandBreakout`,
   finish the wizard, then replace everything in the editor with the contents of `VoltaBandBreakout.cs` and press F5.
   If it shows errors, copy them to Claude with the file - they are expected on a first, never-compiled draft.
2. Open a chart: MNQ (current contract), 1 minute, **Days to load: 25 or more**.
3. Right-click the chart: `Strategies > VoltaBandBreakout`. Account: **Sim101**. Leave the settings at their
   defaults (that is F10's frozen variant #43). Enable it.
4. Open `New > NinjaScript Output`. You should see one line per hourly check, like
   `10:00 CT check: close 28412.25, band 28301.10 .. 28479.90 -> inside, no trade`.

## How it gets its stop

The stop is 0.2 x the day's expected range. That expected range is Volta's own evening forecast, and the frozen rule says
a day without it does not trade. Every evening Volta now writes it to `knowledge/sim_inputs.json`
(`tools/sim_inputs.py`), and the script downloads that small public file at the first check of the day. If the file is
missing, old, or looks wrong, the script prints why and does not trade that day.

## Checking it against Volta (the actual point)

Every closed trade is appended to `Documents\NinjaTrader 8\volta_sim_trades.csv`
(entry/exit time in Chicago time, side, prices, stop size, result in R).
Volta's own simulated trades for the same days are in the forward-test numbers (`/scoreboard`, `families.json`).
For each session compare: same number of trades, same side, entry within a minute, result within 0.05R.
Twenty sessions that match = the first precondition of the eval rule is met. If they do not match, the difference is
the finding - send both logs to Claude before changing anything.

## Known differences to expect

- Volta's backtest is deliberately pessimistic (entry one tick worse, stop wins when stop and target are hit in the same
  bar, target needs one tick through). Real SIM fills will often be slightly better. That is fine within 0.05R.
- If the PC, NinjaTrader or the internet is off during a check, that trade is simply missed.
- F13 (the quick-target variant) is the same script with other settings; they are listed at the top of the `.cs` file.
  F10, F12 and F13 share their entries, so running two of them is not diversification.
