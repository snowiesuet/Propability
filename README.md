# Propability

Propability = Prop Firm + Probability.

## File organization

| Folder | Contents |
| --- | --- |
| [docs/](docs/README.md) | Plans, original requirements, and strategy description |
| [rules/](rules/README.md) | Dated provider references, research, and draft study rules |
| [Strategies/MyStarterPlaybook/](Strategies/MyStarterPlaybook/README.md) | Strategy source, documentation, tests, simulator, logs, versions, and results |

Start here for current project status. Each folder's README provides navigation. Git metadata stays in `.git/`; `.legacy-git/` preserves the former repository metadata.

**Goal:** determine whether the strategy can turn 50 paid prop evaluations into funded accounts and payout income greater than its costs.

## Progress — approximately 30%

Updated October 26, 2026. This is a milestone-based estimate of progress toward the complete 50-account scorecard, not a measured percentage of code complete or a trading success probability. Each milestone below contributes 20 percentage points; the specification is estimated halfway complete.

| Milestone | Status | Progress credit |
| --- | --- | --- |
| Historical data, validation, and single-evaluation prototype | Working foundation; broader platform acceptance remains open | 20% |
| Selected scenario, rules, and execution specification | Scope/settings/research saved; modeling decisions remain | 10% |
| Reusable evaluation/funded account engine | Accounting, loss limits, trailing/evaluation rules tested; historical integration pending | 0% |
| 50-purchase lifecycle, payouts, and cash ledger | Planned | 0% |
| Final scorecard and end-to-end historical acceptance | Planned | 0% |

The existing Python prototype validates the saved 547-trade run and replays one provisional evaluation. Its 13 tests previously passed. It still uses DLL-off/40% rules and is separate from the selected study. **No 50-account lifecycle study has run and no payout results have been calculated.**

## Selected study

- LucidFlex $25K; DLL ON at $600; 50% evaluation consistency; no funded consistency.
- $43.20 per evaluation: $2,160 if all 50 purchases occur. Free funded activation; no reset purchases or monthly budget constraint.
- Fifty sequential evaluation purchases, with funded accounts continuing alongside later evaluations. Respect five-funded/ten-total account limits.
- One MNQ per account. Use completed-trade net results, check loss limits after closed trades, and trail the floor at session end. Intrabar data is deferred and does not block this version.
- Main outputs: trade win rate, average win/loss, evaluation pass/breach rates, funded accounts, payout count/dollars, external costs, and net cash profit. Report unfinished accounts separately.

## Next milestone

**Build the independent account engine now using the [focused implementation plan](docs/plans/ACCOUNT_ENGINE_PLAN.md).** It processes completed trades, session-end drawdown, evaluation passing, funded survival, and DLL lockouts. Remaining payout/coordinator policies can be settled alongside this work; they do not block the standalone engine.

Increments 1–3 are complete: accounting, loss limits, EOD trailing/cap, strict evaluation consistency, funded qualifying days, and unfinished-data handling pass 33 account tests; all 13 existing replay tests still pass. **Next: connect the validated historical run and reconcile both account types, including DLL-skipped trades.** Development policies are explicit; the research draft remains non-executable, and no historical account-engine study has run yet. For a visible synthetic demonstration, run `python Strategies/MyStarterPlaybook/simulator/demo_session_rules.py`.

1. Choose the historical start date and withdrawal timing/amount. A proposed policy is to request the maximum permitted amount while flat after five completed qualifying days, at the next permitted request time; this has not been adopted yet.
2. Resolve the remaining completed-trade rule details: DLL reset/above-trail behavior, floor locking, consistency cushion, qualifying-day/cycle accounting, funded capital, and payout approval/settlement/fees. Keep unsupported values explicit rather than inventing provider rules.
3. Define passed-evaluation waiting when funded slots are full and treatment of discretionary live review.
4. Validate the execution configuration and a hand-calculated account/payout example, then implement reusable account state while preserving the existing replay. Shared account/ledger infrastructure can be developed before every policy is settled; unresolved required rules must be rejected.

After the engine: implement the 50-purchase coordinator, payout/cash ledger, and final Stat / Value scorecard. Net cash profit counts modeled bank receipts minus external costs; account balances and pending payouts are not receipts.

## Project documents

- [Simulator plan, scorecard definitions, and next steps](docs/plans/SIM_PROP_PLAN.md)
- [Independent account-engine implementation plan](docs/plans/ACCOUNT_ENGINE_PLAN.md)
- [Project roadmap](Strategies/MyStarterPlaybook/docs/roadmap.md) and [detailed checklist](Strategies/MyStarterPlaybook/docs/roadmap-detailed.md)
- [Existing simulator usage](Strategies/MyStarterPlaybook/simulator/README.md)
- [Selected FLEX screenshot reference](rules/user_supplied_25k_flex_2026-10-26.md)
- [Official-rule research](rules/lucidflex_25k_research_2026-10-26.md)
- [Draft study configuration](rules/lucidflex_25k_dll_on_50pct_study_draft.json) — research only; not executable with the current replay loader
- [Archived PRO reference](rules/user_supplied_25k_funded_2026-10-26.md) — separate from the active FLEX study
