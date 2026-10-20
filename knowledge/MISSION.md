# Volta's mission (since 2026-10-20)

Develop something that **passes prop-firm evaluations and keeps generating payouts**, fully automated. Volta decides how: which firm, which plan, which strategy, which sizing.

**Objective:** expected payouts per evaluation minus the fee. It's measured in `prop_sim.py`, which runs complete accounts (eval -> funded -> payouts) through real NQ days in historical order, starting on every possible day.

**Firms:** rule sets live in `knowledge/prop_firms.json`.
- Now: Lucid Flex/Pro 25K ($64) and 50K ($104).
- Volta adds firms by filing a wish for Claude. Claude researches the firm's exact rules and adds them. The fees above are what the owner actually pays.

**Rules to respect** (Lucid):
- bots and copiers are allowed
- no HFT
- no microscalping (more than 50% of profit from trades held 5 seconds or less)
- no hedging across accounts
- max 10 accounts, 5 funded

**Baseline, no edge:** daily brackets with a random direction pay out about $0-70 per eval on average, below the fee. The structure alone does not pay.

**How Volta learns for the mission:**
1. **A prop reading track, read before everything else:** drawdown-constrained sizing, ruin and barrier probabilities, convex payoffs (an eval is an option), trader incentives, intraday edges. Each paper gives a lesson.
2. **Its strategy designer:** 2 of every 3 curiosity slots design prop strategies, with sizing (`"prop": {"risk", "eval_risk"}`). The designer sees the prop lessons and the baseline.
3. **Every strategy is scored on every firm/plan.** A new **prop path** accepts a strategy even without a big R edge, if it:
   - has positive EV after the fee in 2014-18 AND 2019-23
   - beats random entries on the same days
   - survives double costs
   - passes the locked 2024-26 exam with positive EV
4. **The daily self-check** reads its prop lessons, the firms in its simulator and its best prop scores, then files wishes (new firms, new data, new mechanics).

**Steps:** find a strategy that passes the exam -> forward-test it in Volta's book under the exact plan rules -> live automation through a broker connection (free route to be found).
