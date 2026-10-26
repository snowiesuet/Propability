# FairPriceStrategy Roadmap

Paths in code examples and data-folder references are relative to `Strategies/MyStarterPlaybook/` unless stated otherwise. Document links resolve from this file.

Last updated: October 26, 2026 (America/New_York)

## Account-engine increments

- [x] Completed-trade accounting foundation: Decimal P&L, single commission deduction, independent accounts, net statistics, closed-trade drawdown, and atomic invalid-input rejection. Nine new tests and all 13 legacy tests pass; trading-body hashes match.
- [x] Explicit development rules, fixed loss-floor breaches, DLL lockouts, terminal protection, and observed session closure/reset. Twelve new tests pass; total 21 account tests plus 13 legacy tests.
- [x] EOD trailing/cap, evaluation target/strict consistency, funded qualifying days, and unfinished data handling. Twelve new tests pass; total 33 account tests plus 13 legacy tests. Synthetic fixtures only; historical adapter is next.
- [ ] Validated historical adapter and reconciliation for evaluation/funded accounts, including skipped trades.

See the [implementation checkpoints](../../../docs/plans/ACCOUNT_ENGINE_PLAN.md#incremental-delivery-checkpoints). The accounting ledger includes all supplied trades; the engine enforces explicit fixed/EOD trailing, DLL, and stage-specific development rules. Qualifying-day counts alone do not establish payout eligibility. The research draft remains non-executable.

Current stage: **Single-evaluation Python prototype implemented and current 547-trade baseline reconciled with Analyzer.** Layering-disabled ON/OFF trade comparison passed; full platform acceptance, measured costs, and authoritative provider rules remain open. The next milestone is the execution specification for the 50-purchase FLEX lifecycle study; start-date batches are deferred.

Requirements: [objective.md](../../../docs/requirements/objective.md). Project context: [project.md](project.md). Logging details: [LOGGING.md](LOGGING.md).

Checked items represent completed artifacts or checks. An implemented component still needs the platform acceptance tasks below before it is considered validated end to end. Update this checklist when work is completed and record the supporting run or report.

## 1. Strategy and logging foundation — implemented

- [x] Identify `NYOpenFairPriceStrategy` as the active FairPriceStrategy / Cont & Rev implementation.
- [x] Document existing entry, exit, risk, calculation mode, and managed-order behavior.
- [x] Add configurable CSV logging with a separate helper and unique run directories.
- [x] Implement actual execution logging, including partial-fill accounting.
- [x] Implement closed trade-segment matching, reversal accounting, and commission modes.
- [x] Implement sampled strategy equity observations and primary-bar export.
- [x] Implement run metadata, final inventory, completeness flags, and failure reporting.
- [x] Document output schemas, setup, accounting conventions, and sampling limits.
- [x] Add standalone C# fixtures, Python CSV/accounting checks, and trading-body integrity checks.
- [x] Rerun standalone accounting/CSV and trading-body integrity checks on October 25, 2026.
- [x] Save the MNQ baseline in `logs/logging-on/0.1/`.
- [x] Capture the dated LucidFlex $25K rules reference and unresolved inputs.
- [x] Replace the old ATRManager project plan with the FairPriceStrategy prop firm objective.

Evidence: [source](../NYOpenFairPriceStrategy.cs), [logger](../ContRevCsvLogger.cs), [tests](../tests), [baseline metadata](../logs/logging-on/0.1/run_metadata.json), and [rules snapshot](../../../rules/lucidflex_25k_2026-10-22.md). pandas ingestion was not rerun because pandas was unavailable.

## 2. NinjaTrader acceptance — remaining platform work

Latest evidence: [Phase 2 comparison review](../logs/phase2-comparison-review.md). The inspected logging-OFF/ON individual Trades exports matched all 547 rows and 23 columns with layering disabled; summary exports also matched. The current `logs/logging-on/0.1/` contains the matching 547-segment logger run and Analyzer exports, reconciled by the Python validator. The current OFF archive contains daily Analysis rows again; restoring its individual Trades export remains necessary for a fresh reproducible ON/OFF comparison. Full acceptance remains open.

- [x] Compile the strategy and logger integration in NinjaTrader (user confirmed NYOpen compilation and successful CSV export; October 25, 2026).
- [x] Complete logging-OFF and logging-ON Analyzer runs with layering disabled (user reported).
- [x] Inspect the logging-OFF settings screenshot; logging and layering are disabled.
- [x] Compare the two supplied summary files; all exported values match exactly.
- [x] Save the comparison review with trade-level findings, hashes, and remaining limits.
- [x] Save matching logging-ON Summary and individual Trades exports under `logs/logging-on/0.1/`.
- [x] Compare individual ON/OFF Trades exports with layering disabled: all 547 rows and 23 columns match.
- [ ] Restore and retain the logging-OFF individual Trades export; the current archive contains daily Analysis rows.
- [ ] Save logging-ON settings and verify all Analyzer inputs match the logging-OFF run except the logging switch.
- [x] Save the matching 547-segment logger run in `logs/logging-on/0.1/`; the older 542-segment run is no longer present at that path.
- [x] Reconcile the current ON logger's executions, completed trades, and flat final inventory with Analyzer using the Python validator.
- [ ] Retain an original pre-instrumentation strategy baseline and compare it against the instrumented variants using identical inputs.
- [ ] Repeat the logging-OFF versus logging-ON comparison with layering enabled; layering has not been tested yet.
- [ ] Verify stops, targets, and session-close exits in the platform comparisons.
- [ ] Verify partial fills, partial exits, reversals, and orderless fills where replay/platform data permits; document unavailable cases.
- [ ] Check overnight exchange trading dates and DST handling against NinjaTrader.
- [ ] Verify file-path failures disable logging without interrupting trading.
- [ ] Finalize the acceptance report with run identifiers, matched settings, trade-level results, and unresolved cases.

Remaining platform priorities: retain logging-ON settings and restore the OFF individual Trades export, then complete layering-enabled and other platform edge-case comparisons. These remain open alongside the next Python milestone.

Completion gate: platform evidence shows logging preserves the strategy's trading behavior. Matching summary totals alone do not establish matching individual trades or complete Phase 2.

## 3. Complete the instrumentation requirements

- [ ] Implement `orders.csv` with order lifecycle states, changes, cancellations, rejections, and reliable identifiers.
- [ ] Document/version the mapping from `equity.csv` to objective.md's `account_equity.csv` requirements, including starting balance and derived account state.
- [ ] Add or derive explicit session transitions, starting state, and daily reset information.
- [ ] Produce `sessions.csv` with daily P&L, costs, trade counts, and clearly labeled sampled equity/drawdown extrema.
- [ ] Audit metadata against every requested field, including strategy/logging version, platform version when available, capital assumptions, and requested versus observed run range.
- [ ] Investigate historical tick/replay observations without changing strategy execution behavior.
- [ ] Define conservative bounds or explicit uncertainty for cases without sufficient intrabar observations.
- [ ] Extend fixtures and schema checks for the new outputs and accounting paths.
- [ ] Recheck trading-body integrity and repeat affected platform comparisons after instrumentation changes.
- [ ] Update `LOGGING.md` with all new fields, limitations, and export instructions.

Completion gate: required outputs or explicitly agreed schema mappings exist, with no invented fills, balances, costs, or intrabar certainty.

## 4. Reconciled historical baseline

- [ ] Enable pandas ingestion validation in the working Python environment.
- [x] Create a reusable validator for actual exported runs, beyond standalone fixtures.
- [x] Validate schemas, identifiers, timestamps, missing values, completion status, accounting quality, and open inventory.
- [x] Generate a commission-aware baseline or explicitly cost the existing gross fills once using the selected assumption.
- [ ] Export the matching Strategy Analyzer results and exact run settings.
- [x] Reconcile gross execution/trade P&L, sampled equity, and ending inventory for the current run; Analyzer costs are zero and logger commissions unknown.
- [x] Reconcile daily gross totals and execution/trade counts for the current run.
- [ ] Validate measured commissions and cost-bearing platform accounting; current fixed costs remain a scenario assumption.
- [x] Save a per-run validation report that flags discrepancies without silently correcting them.

Current baseline: `logs/logging-on/0.1/` now contains the 1,094-execution, 547-segment run with -$2,432.50 gross P&L. It reconciles with Analyzer in the Python validator; costs remain assumed and historical Last ticks are absent.

## 5. Prop firm rules and simulation policies

Active scope: [50-purchase plan](../../../docs/plans/SIM_PROP_PLAN.md). Follow its [current next steps](../../../docs/plans/SIM_PROP_PLAN.md#current-status-and-next-step).

- [x] Confirm FLEX $25K; retain PRO separately as an archived reference.
- [x] Record DLL ON at $600, 50% evaluation consistency, no funded consistency, five $100 profit days, and free activation.
- [x] Confirm $43.20 per purchase ($2,160 for 50), sequential attempts, no monthly budget constraint, and no reset purchases.
- [x] Save screenshot evidence, official-rule research, and a separate draft configuration; preserve the existing executable configuration.
- [x] Validate draft JSON syntax and selected price/count settings; this is not execution acceptance.
- [x] Record five-funded/ten-total limits and discretionary live-transition constraints.
- [ ] Resolve DLL session reset and funded above-trail behavior; use realized net losses after completed trades for this version.
- [ ] Resolve floor lock boundary/rounding and withdrawal/floor ordering; intraday enforcement and liquidation are deferred.
- [ ] Resolve consistency cushion, qualifying-day accounting, funded capital, and payout-cycle reset.
- [ ] Obtain the user's historical start date and withdrawal timing/amount policy.
- [ ] Define funded-slot waiting, live-review handling, approval/receipt timing, and pending payouts after termination.
- [ ] Confirm calendar/timezone interpretation and additional external fees.
- [x] User approved completed-trade results: closed-trade loss checks, session-end floor updates, and no intrabar/liquidation data requirement. Document the limitation; do not fabricate early exits.
- [ ] Produce a validated execution configuration rejecting unresolved required inputs.

Evidence: [research](../../../rules/lucidflex_25k_research_2026-10-26.md), [screenshots](../../../rules/user_supplied_25k_flex_2026-10-26.md), [draft JSON](../../../rules/lucidflex_25k_dll_on_50pct_study_draft.json).

Completion gate: every required mechanic has evidence or a named approved modeling policy. Phase 1 remains open; the draft is not compatible with the existing replay loader.

## 6. Python simulator

- [x] Ingest validated runs and normalize event time/order without using future information.
- [x] Implement configurable starting balance and gross/net accounting with fixed commissions deducted once for one-contract replay.
- [x] Implement provisional 18:00 Eastern source-clock sessions and observed session-end events; leave the final session unclosed without a rollover.
- [x] Implement provisional EOD trailing floor, cap, equality breaches, target, strict 40% consistency, and pass/breach/incomplete outcomes.
- [ ] Add quantity scaling and validated support for additional inventory cases.
- [ ] Confirm provider session/calendar rules and add any required minimum/qualifying-day policies.
- [ ] Add static and intraday trailing drawdown modes as configuration requires.
- [ ] Implement daily loss lockouts and account-ending breaches as distinct outcomes.
- [ ] Implement funded progression, scaling, payout eligibility, withdrawals, and profit splits.
- [ ] Implement 50 sequential purchases and applicable costs without a monthly budget or paid resets in this study.
- [x] Emit account event histories and trace each result to the source run and rule configuration.
- [x] Add tests for evaluation boundaries, equality breaches, session rollover, costs, consistency, and incomplete data behavior (13 tests recorded in the prototype evidence).
- [ ] Test activation rebasing, account isolation, standalone/coordinator agreement, account limits, and incomplete lifecycle outcomes.
- [ ] Validate funded/payout examples and fee/payout/drawdown ordering before extending the account lifecycle.

Completion gate: the supported account engine and 50-purchase lifecycle reconcile against manual fixtures and validated historical observations, including cash accounting and explicit uncertainty.

### Next milestone — execution specification, then lifecycle implementation

- [ ] Close remaining section 5 rule/policy gaps using the approved completed-trade model.
- [ ] Refactor reusable evaluation/funded state without changing existing replay results.
- [ ] Implement a study CLI/coordinator: one evaluation, up to five funded accounts, maximum 50 actual purchases.
- [ ] Include payout requests, approvals, account deductions, bank receipts, and fees in the first release.
- [ ] Verify manually reconciled multi-account fixtures, independent funded failures, and account activation timing.
- [ ] Test DLL lockouts, drawdown floors, consistency/winning days, session/DST ordering, and cost deductions.
- [ ] Validate per-account standalone/coordinator agreement and report provenance.
- [ ] Report actual purchases if data ends before 50; never repeat source history to fill the count.

Acceptance: current replay remains reproducible, new fixtures reconcile, and uncertain/incomplete outcomes remain explicit. The lifecycle CLI is planned, not implemented. No 50-attempt study has run.

## 7. Comparisons and final findings

- [ ] Deliver the [Stat / Value scorecard](../../../docs/plans/SIM_PROP_PLAN.md#primary-goal-and-scorecard): source trade win rate and average win/loss, actual evaluation pass/breach/pending counts, funded activation, payouts, external costs, and net cash profit.
- [ ] Verify metric denominators, exclude copied-account duplication from source trade statistics, use N/A for empty samples, and reconcile every scorecard value with account/cash traces.
- [ ] Report evaluation outcomes, funded survival, terminal reasons, and actual attempt counts.
- [ ] Reconcile qualifying days, payout events, external costs, and net bank cash results to account/cash traces.
- [ ] Label intrabar, liquidation, and settlement approximations; preserve input/rule/code hashes.
- [ ] Publish reproducible run references and findings with uncertainty.
- [ ] Later: compare full-lifecycle historical starts, sizing, and checkout variants.
- [ ] Later: define budget, reinvestment, and reset-policy variants separately.

Completion gate: historical outcomes and cash results reconcile to supported inputs and selected policies. Historical replay is not a forecast.

## Maintenance

- Keep completed boxes backed by a file, test result, or saved report.
- Keep implemented components separate from platform-validated acceptance.
- Update this roadmap and `project.md` together when scope or status changes.
- Preserve dated rules and baseline runs; add new versions when inputs change.
- Keep strategy optimization and the earlier ATRManager work outside this roadmap unless separately authorized.

## Python prototype progress

A one-contract, no-layering DLL-off/40% evaluation scenario is implemented with explicit 18:00 source-clock sessions, EOD trailing floor, fixed commissions, pass/breach/incomplete outcomes, event history, and hashed versioned reports. Thirteen boundary/reconciliation tests pass, and the current real run validates against Analyzer. Broader grouped simulator boxes remain open because alternate drawdown modes, scaling, DLL-on, funded stages, payouts, and repeated attempts are not implemented.

See [usage](../simulator/README.md) and [first validated result](../simulation-results/v0.1/20261025T202249Z_3fbf4a08/report.md). Earlier Phase 2 export-path notes describe evidence before the user reorganized the folders; use the run manifest and report hashes for current provenance.
