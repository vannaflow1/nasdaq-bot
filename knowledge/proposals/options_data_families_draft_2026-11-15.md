# DRAFT - what to test on the intraday option-chain archive

**Status: draft for the owner. Not registered. No alpha slot spent. Nothing frozen. Nothing scored.**
Written 15 Nov 2026 by Claude (Fable 5.2) during the "upgrade" session.

**Peek disclosure:** I looked at the *layout* of `knowledge/data/chains/` (folder names, the column list in
`tools/chain_snap.py`, the number of session folders: 10). I did not open any snapshot, compute any statistic, or
relate any option number to any price move. The three ideas below come from the mechanism, not from the data.

## The short version (plain words)

- The archive started on 1 Nov 2026. It grows by about 21 sessions a month.
- The briefing suggested scoring new families "once 6-8 weeks exist". **The maths says that is too early for anything
  that trades direction.** With ~40 sessions a test can only see an edge of about +0.75R per trade. Volta's one
  surviving idea is +0.03R. A realistic direction edge (+0.1 to +0.2R) needs roughly 600 to 2,300 trades, i.e. years.
- Predicting **how big the afternoon will be** is different: option prices are good at that, and a relationship of
  that strength can be judged with about 60 sessions (end of January 2027).
- So my recommendation is: **one study now-ish (O3, no slot needed), two direction ideas written down but parked**
  until the archive is big enough, and **keep both fast slots and the last v2 slot unspent**.

## What the free data can and cannot show (important)

| Thing | Available? |
|---|---|
| 0DTE and next-expiry quotes (bid/ask), IV, greeks, every ~5 min, strikes within 4% of spot | yes |
| ATM straddle price, ATM IV, 25-delta put and call IV per expiry (the `_surface` files) | yes |
| Volume per strike during the day | yes (cumulative) |
| Open interest changing **during** the day | **no** - CBOE publishes yesterday's OI. "Intraday dealer-gamma shift" is therefore not observable; anything called GEX intraday is yesterday's positions re-priced at today's spot. |
| Real-time prices | **no** - quotes are ~15 minutes delayed. A live signal at 12:00 uses 11:45 option prices. Every test below must use the same delay (signal from quotes stamped at least 15 min before the decision time), or it tests something that cannot be traded. |
| Who bought and who sold | no |

## How many cases a test needs (power)

Direction trades (mean R per trade, noise assumed 1.5R per trade, 80% chance to detect):

| True edge per trade | Trades needed at alpha 0.01 (fast slot) | at alpha 0.0023 (last v2 slot) |
|---|---|---|
| +0.10R | 2,259 | 3,040 |
| +0.20R | 565 | 760 |
| +0.30R | 251 | 338 |
| +0.50R | 91 | 122 |
| +0.75R | 41 | 55 |

"How big will the afternoon be" (a correlation between a midday signal and the afternoon range):

| True correlation | Sessions needed at 5% (study route) | at 1% |
|---|---|---|
| 0.2 | 154 | 248 |
| 0.3 | 68 | 108 |
| 0.4 | 38 | 59 |
| 0.5 | 24 | 37 |

Calendar: about 50 sessions by mid-January 2027, 60 by the end of January, 110 by mid-April, 250 by November 2027.

## O3 - front-end volatility bid at midday -> bigger afternoon (recommended first)

- **Mechanism.** When traders pay up for same-day options relative to next-day options during the morning, they expect
  the afternoon to move. Realized range tends to follow implied.
- **Signal** (decided at 12:00 New York, from quotes stamped 11:45 or earlier): the ratio of 0DTE ATM IV to
  next-expiry ATM IV, divided by the same ratio at 09:45. Above 1 = the front end got bid during the morning.
- **Outcome.** NQ high-low range from 12:00 to 16:00 New York, divided by the median of that same window over the
  previous 14 sessions (so a quiet regime and a wild regime are comparable).
- **Test.** Spearman correlation between signal and outcome, one-sided (higher ratio -> larger range). One look.
- **Variants (18):** signal time {11:30, 12:00, 12:30} x far leg {next expiry, ~7 days, ~30 days} x symbol {QQQ, NDX}.
  Reported as the median across variants plus the share of variants with the right sign, as families do.
- **When.** First and only look at 60 sessions with complete morning data. Before that: nobody opens the files.
- **What a pass would give.** Not a trade. A tested midday update to the day-size outlook ("the afternoon is likely
  bigger/smaller than usual"), and a pre-declared candidate filter for F13's afternoon trades - which would then need
  its own registered test.
- **Slot.** None. This is an owner-facing input like the day-size outlook (`tools/overnight_study.py` route:
  pre-declared, one look, no alpha slot). If you would rather run it as a family, it would take the last v2 slot
  (alpha 0.0023) and then needs a correlation of about 0.45 at 60 sessions to pass.

## O1 - the day has already used its implied move and options are not cheapening -> continuation (parked)

- **Mechanism.** The morning straddle prices a day move. If by midday price has already travelled most of it and the
  remaining 0DTE straddle is not decaying the way time alone predicts (IV rising), the market is repricing to a trend day.
- **Signal** at t: used = |spot_t / open - 1| / (09:45 straddle / spot); iv_up = 0DTE ATM IV at t / at 09:45 - 1.
  Trade when used >= X and iv_up >= Y, in the direction of open -> t.
- **Trade.** NQ at t (using the 15-minute-old option quotes), stop 0.5 x the remaining straddle-implied move, exit 15:55
  New York, one trade a day.
- **Variants (27):** t {11:00, 12:00, 13:00 NY} x X {0.6, 0.8, 1.0} x Y {none, 0%, +5%}.
- **Test.** Mean net R per trade, null v3 (shared sign flips), placebo twins - the standard family procedure.
- **Honest power.** Maybe 1 trade every 2-3 sessions. 250 trades (enough for +0.3R) is about 2.5 years. **Park it.**
  Registering it now would spend a slot on a test that almost certainly ends "failed: underpowered".

## O2 - skew steepens while price holds -> next hour down (parked)

- **Mechanism.** Put buyers hedge before the move; 25-delta put IV rising relative to call IV while price is not
  falling is the footprint. The mirror (call skew, price not rising) for longs.
- **Signal** at each hourly check 10:30-14:30 NY: change of (25-delta put IV - 25-delta call IV) on the 0DTE expiry over
  the last 30 or 60 minutes, as a z-score against the same-time changes of the previous 10 sessions; price change over
  the same window must be >= 0 for a short (<= 0 for a long).
- **Trade.** NQ against the skew move's implication for 30 or 60 minutes, stop 0.25% of price, time exit.
- **Variants (36):** lookback {30, 60} x z {1.0, 1.5, 2.0} x hours {all, morning only, afternoon only} x hold {30, 60}.
- **Test.** As O1.
- **Honest power.** Perhaps one trade a session: +0.3R needs a year, +0.2R more than two. Also the 15-minute delay
  eats most of a 30-60 minute signal. **Park it**, or drop it.

## What I am asking you to decide

1. **O3: yes or no?** If yes: as a study (no slot, my recommendation) or as a family on the last v2 slot?
2. **O1 and O2:** keep them parked here as written (my recommendation), or drop them?
3. **The two fast slots:** stay unspent until an idea shows up that can actually be judged in the time you care about.
   The data to judge a fast direction edge on options does not exist yet and cannot be bought for free.

Nothing happens until you answer. If you say yes to O3, the next step is a commit that freezes this spec (hash recorded),
a small script that builds the signal and outcome series without printing them, and a calendar entry for the one look.
