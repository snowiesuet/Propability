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

## Progress — approximately 60%

Updated November 3, 2026. This is a milestone-based estimate toward the complete 50-purchase scorecard, not a measured percentage of code complete or a trading success probability. Each milestone contributes up to 20 percentage points; partially implemented milestones receive partial credit.

| Milestone | Status | Progress credit |
| --- | --- | --- |
| Historical data, validation, and single-evaluation prototype | Working foundation; broader platform acceptance remains open | 20% |
| Selected scenario, rules, and execution specification | Scope/settings/research saved; modeling decisions remain | 10% |
| Reusable evaluation/funded account engine | Accounting, loss limits, trailing/evaluation rules and historical adapter implemented | 20% |
| 50-purchase lifecycle, payouts, and cash ledger | Coordinator/report implemented; only 10 purchases supported by available history; assumptions and fixtures remain | 10% |
| Final scorecard and end-to-end historical acceptance | Planned | 0% |

The legacy Python prototype still uses DLL-off/40% rules and remains separate from the selected study. The new lifecycle runner validated the saved 547-trade run, but the available chronological history supported only 10 purchases; it produced 2 passes, 7 breaches, 1 unfinished evaluation, and 2 unfinished funded accounts. No payout receipts were observed, so a complete 50-purchase result is not available yet. New hand-calculated and synthetic lifecycle fixtures exercise payout 1, payout 5, live promotion, bonus receipt, the 50-purchase cap, and cash reconciliation; all 49 simulator tests pass.

## Selected study

- LucidFlex $25K; DLL ON at $600; 50% evaluation consistency; no funded consistency.
- $43.20 per evaluation: $2,160 if all 50 purchases occur. Free funded activation; no reset purchases or monthly budget constraint.
- Fifty sequential evaluation purchases, with funded accounts continuing alongside later evaluations. Account capacity limits are excluded from this study by user choice.
- One MNQ per account. Use completed-trade net results, check loss limits after closed trades, and trail the floor at session end. Intrabar data is deferred and does not block this version.
- Main outputs: trade win rate, average win/loss, evaluation pass/breach rates, funded accounts, payout count/dollars, external costs, and net cash profit. Report unfinished accounts separately.

## Next milestone

**Extend the validated historical input to complete the 50-purchase run.** The coordinator, payout/cash ledger, Stat / Value report, and initial LucidLive tracker are implemented; payout, live, and cap paths reconcile in synthetic fixtures, and all 49 simulator tests pass. The only validated strategy run in the workspace supports 10 purchases, producing 2 passes, 7 breaches, 1 unfinished evaluation, and 2 funded accounts unfinished at data end. It had no payouts and -$432 net cash before unverified fees. A complete 50-purchase result needs a longer validated historical trade stream; the current files contain no second run.

Increments 1–4 are complete: accounting, loss limits, EOD trailing/cap, strict evaluation consistency, funded qualifying days, unfinished-data handling, and the validated historical adapter are implemented. The quick sequential cohort run used all 547 validated trades: 2 evaluations passed, 7 breached, and 1 remained unfinished. A new evaluation started after each pass or breach; funded-account continuation and payouts were excluded. This is a preliminary count under $600 DLL, strict 50% consistency, and completed-trade checks, not a full lifecycle estimate. Run `python Strategies/MyStarterPlaybook/simulator/account_cohort.py`; output goes to a new folder under `Strategies/MyStarterPlaybook/simulation-results/account-cohort/`.

1. **Selected:** start January 1, 2026; request the maximum permitted payout at the first eligible time the funded account is flat, using 50% of current payout-cycle net profit (up to $1,000; $500 minimum). Treat payout approval and receipt as immediate; ignore payout processing, settlement, and post-request trading pauses. The five qualifying-day rule still applies.
2. Review the current [interactive lifecycle dashboard](Strategies/MyStarterPlaybook/simulation-results/lifecycle-study/latest/dashboard.html), [scorecard and account table](Strategies/MyStarterPlaybook/simulation-results/lifecycle-study/latest/report.md), [account-by-account CSV](Strategies/MyStarterPlaybook/simulation-results/lifecycle-study/latest/account-lifecycle.csv), and [per-session trade summary](Strategies/MyStarterPlaybook/simulation-results/lifecycle-study/latest/session-summary.csv). The dashboard combines the summary, filters, session results, account traces, assumptions, limitations, validation, and source links. The CSV has 10 evaluation attempts and the session file has 195 rows totaling 547 trades; detailed per-account traces remain in the JSON. The simulator replaces these `latest` reports on each default run. Use `--out` when a separately saved comparison run is useful. Also review the [first payout fixture](docs/plans/LIFECYCLE_HAND_CHECK.md) and [payout-5/live fixture](docs/plans/LIFECYCLE_LIVE_HAND_CHECK.md). Retain the DLL-above-trail, consistency-cushion, qualifying-day, and unknown fee limitations in future reports.
3. Provide/import a longer validated Analyzer/logger run. Do not replay or duplicate the existing 547 trades to fill the missing 40 purchases.

Net cash profit counts modeled bank receipts minus external costs; account balances and pending payouts are not receipts. A single chronological replay does not yield repeated-cycle probabilities.

## Project documents

- [Simulator plan, scorecard definitions, and next steps](docs/plans/SIM_PROP_PLAN.md)
- [Stat / Value scorecard template](docs/plans/SCORECARD_TEMPLATE.md)
- [Independent account-engine implementation plan](docs/plans/ACCOUNT_ENGINE_PLAN.md)
- [Hand-calculated evaluation and payout example](docs/plans/LIFECYCLE_HAND_CHECK.md)
- [Payout-5 and live-stage hand check](docs/plans/LIFECYCLE_LIVE_HAND_CHECK.md)
- [LucidLive rule tracker](Strategies/MyStarterPlaybook/simulator/live_stage.py)
- [Lifecycle policy choices for review](docs/plans/LIFECYCLE_POLICY_REVIEW.md)
- [Project roadmap](Strategies/MyStarterPlaybook/docs/roadmap.md) and [detailed checklist](Strategies/MyStarterPlaybook/docs/roadmap-detailed.md)
- [Existing simulator usage](Strategies/MyStarterPlaybook/simulator/README.md)
- [Selected FLEX screenshot reference](rules/user_supplied_25k_flex_2026-10-26.md)
- [Official-rule research](rules/lucidflex_25k_research_2026-10-26.md)
- [Draft study configuration](rules/lucidflex_25k_dll_on_50pct_study_draft.json) — research only; not executable with the current replay loader
- [Archived PRO reference](rules/user_supplied_25k_funded_2026-10-26.md) — separate from the active FLEX study
