# Volta's mission (since 2026-10-20)

Become an automated trader that passes prop-firm evaluations (Lucid, 25K first) and keeps generating payouts.

**Objective:** expected payouts per evaluation minus the evaluation fee, measured in `prop_sim.py`, which runs complete accounts (eval -> funded -> payouts) through real NQ days under Lucid's rules.

**Constraints:** Lucid's automation rules:
- bots and copiers are allowed
- no HFT
- no microscalping (more than 50% of profit from trades held under 5 seconds)
- no hedging across accounts
- max 10 accounts per household, 5 funded

**Baseline, a strategy with no edge** (simple daily brackets, random direction): $0-70 median paid out per eval, max ~$220, and inconsistent between 2014-21 and 2022-26. The structure alone does not pay. Volta needs a real edge, shaped to the rules.

**Every strategy the lab tests now gets a prop score** (pass rate, $ paid out per eval). The strategy designer and the daily self-check are told this mission.

Steps:
1. Prop-score everything.
2. Search the strategy space with the prop objective.
3. Forward-test the winner on the virtual book with Lucid's exact rules.
4. Only then, live automation through a broker connection.
