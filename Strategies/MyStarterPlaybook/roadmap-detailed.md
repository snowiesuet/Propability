# FairPriceStrategy Roadmap

Last updated: October 25, 2026 (America/New_York)

Current stage: **Phase 2 — NinjaTrader compilation confirmed; supplied summaries match; individual-trade acceptance pending.** The Python prop firm simulator has not been built.

Requirements: [objective.md](../../objective.md). Project context: [project.md](project.md). Logging details: [LOGGING.md](LOGGING.md).

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

Evidence: [source](NYOpenFairPriceStrategy.cs), [logger](ContRevCsvLogger.cs), [tests](tests/), [baseline metadata](logs/logging-on/0.1/run_metadata.json), and [rules snapshot](../../rules/lucidflex_25k_2026-10-22.md). pandas ingestion was not rerun because pandas was unavailable.

## 2. NinjaTrader acceptance — current phase

Latest evidence: [Phase 2 comparison review](logs/phase2-comparison-review.md). The two supplied summary exports are byte-for-byte identical: 547 trades, -$2,432.50 total P&L, -$5,900.50 maximum drawdown, and $0 commissions. The summary at the logs root still needs confirmation as the logging-ON export. Full acceptance remains open.

- [x] Compile the strategy and logger integration in NinjaTrader (user confirmed NYOpen compilation and successful CSV export; October 25, 2026).
- [x] Complete logging-OFF and logging-ON Analyzer runs with layering disabled (user reported).
- [x] Inspect the logging-OFF settings screenshot; logging and layering are disabled.
- [x] Compare the two supplied summary files; all exported values match exactly.
- [x] Save the preliminary comparison review with findings and missing evidence.
- [ ] Confirm the root `logs/analyzer-summary.csv` is the logging-ON summary, or save a clearly labeled replacement under `logs/logging-on/`.
- [ ] Export individual trades using Display > Trades from the logging-OFF run. The current `analyzer-trades.csv.csv` contains daily Analysis rows.
- [ ] Export individual trades using Display > Trades from the equivalent logging-ON run.
- [ ] Save logging-ON settings and verify all Analyzer inputs match the logging-OFF run except the logging switch.
- [ ] Save the newly generated logger run folder matching the 547-trade Analyzer run. Preserve `logs/logging-on/0.1/` as the older baseline: it ends October 21 with 542 closed segments and -$2,182.50 gross P&L.
- [ ] Compare individual entry/exit timestamps, direction, quantities, prices, signals, P&L, executions, and final inventory across the matching runs.
- [ ] Retain an original pre-instrumentation strategy baseline and compare it against the instrumented variants using identical inputs.
- [ ] Repeat the logging-OFF versus logging-ON comparison with layering enabled; layering has not been tested yet.
- [ ] Verify stops, targets, and session-close exits in the platform comparisons.
- [ ] Verify partial fills, partial exits, reversals, and orderless fills where replay/platform data permits; document unavailable cases.
- [ ] Check overnight exchange trading dates and DST handling against NinjaTrader.
- [ ] Verify file-path failures disable logging without interrupting trading.
- [ ] Finalize the acceptance report with run identifiers, matched settings, trade-level results, and unresolved cases.

Immediate next step: save the correctly labeled Summary, individual Trades exports, logging-ON settings, and matching new logger output. Finish the layering-disabled trade comparison before testing layering enabled.

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
- [ ] Reconcile execution realized P&L, closed trade-segment P&L, total commissions, and ending equity/inventory.
- [ ] Reconcile session/daily totals and execution/trade counts, explaining matching-policy differences.
- [x] Save a per-run validation report that flags discrepancies without silently correcting them.

Current baseline: `logs/logging-on/0.1/` now contains the 1,094-execution, 547-segment run with -$2,432.50 gross P&L. It reconciles with Analyzer in the Python validator; costs remain assumed and historical Last ticks are absent.

## 5. Prop firm rules and simulation policies

- [ ] Confirm provider identity: objective.md says Lucify; the available reference covers Lucid Trading / LucidFlex $25K.
- [x] Define a versioned Python configuration schema separate from NinjaScript.
- [ ] Capture actual checkout prices and applicable fees for all four DLL/consistency configurations.
- [ ] Resolve DLL amount, equity/cost basis, lockout behavior, and reset time.
- [ ] Resolve consistency cushion, rounding, and winning-day calculation.
- [ ] Resolve intraday drawdown enforcement, EOD trailing updates, lock boundaries, and event ordering.
- [ ] Define provider timezone, sessions, holidays, trading cutoffs, and DST interpretation.
- [ ] Define evaluation-to-funded balance reset, activation timing, and funded scaling.
- [ ] Define qualifying days, payout cycles, approval timing, profit splits, and withdrawal effects on drawdown.
- [ ] Choose whether replay stops at live review or uses an explicitly hypothetical live-transition policy.
- [ ] Define the $500 monthly purchase budget policy, including carryover, repurchases, resets, parallel accounts, and payout reinvestment.
- [ ] Preserve unresolved rules as unknowns or named scenarios and link each rule to its dated source.

Completion gate: each simulated scenario has explicit rules, costs, assumptions, and lifecycle policies.

## 6. Python simulator

- [x] Ingest validated runs and normalize event time/order without using future information.
- [ ] Implement configurable starting balances, quantity scaling, gross/net accounting, and commissions without double-counting.
- [ ] Implement provider sessions, daily resets, and session-end events.
- [ ] Implement static, intraday trailing, and EOD trailing drawdown modes as configuration requires.
- [ ] Implement daily loss lockouts and account-ending breaches as distinct outcomes.
- [ ] Implement evaluation targets, consistency, qualifying/minimum days, and pass/fail states.
- [ ] Implement funded progression, scaling, payout eligibility, withdrawals, and profit splits.
- [ ] Implement purchase/reset/activation costs and repeated attempts under the budget policy.
- [x] Emit account event histories and trace each result to the source run and rule configuration.
- [ ] Test boundary equality, session rollover, fee timing, payout/drawdown ordering, and incomplete data behavior.
- [ ] Validate small hand-calculated evaluation, breach, and payout examples before batch replay.

Completion gate: one configured account lifecycle reconciles end to end before repeated-attempt comparisons.

## 7. Comparisons and final findings

- [ ] Compare the four DLL on/off and 40%/50% consistency configurations.
- [ ] Compare MNQ sizing from 1–10 micros per entry, enforcing configured position limits.
- [ ] Replay multiple historical start dates with explicit data-end/censoring handling.
- [ ] Report evaluation outcomes, breach reasons, attempt counts, and time to pass.
- [ ] Report funded survival, qualifying days, payout timing, and payouts actually modeled as received.
- [ ] Report purchase/reset/activation costs and net cash results under the monthly budget.
- [ ] Test sensitivity to fees, costs, fill assumptions, and unresolved provider rules.
- [ ] Label sampled intrabar outcomes, bounds, and quantity-scaling assumptions in every comparison.
- [ ] Publish reproducible run/configuration references and a concise findings report.

Completion gate: the results explain how FairPriceStrategy performed under each modeled prop firm system, including failure costs and uncertainty. Historical replay outcomes must remain distinct from forecasts.

## Maintenance

- Keep completed boxes backed by a file, test result, or saved report.
- Keep implemented components separate from platform-validated acceptance.
- Update this roadmap and `project.md` together when scope or status changes.
- Preserve dated rules and baseline runs; add new versions when inputs change.
- Keep strategy optimization and the earlier ATRManager work outside this roadmap unless separately authorized.

## Python prototype progress

A one-contract, no-layering DLL-off/40% evaluation scenario is implemented with explicit 18:00 source-clock sessions, EOD trailing floor, fixed commissions, pass/breach/incomplete outcomes, event history, and hashed versioned reports. Thirteen boundary/reconciliation tests pass, and the current real run validates against Analyzer. Broader grouped simulator boxes remain open because alternate drawdown modes, scaling, DLL-on, funded stages, payouts, and repeated attempts are not implemented.

See [usage](simulator/README.md) and [first validated result](simulation-results/v0.1/20261025T202249Z_3fbf4a08/report.md). Earlier Phase 2 export-path notes describe evidence before the user reorganized the folders; use the run manifest and report hashes for current provenance.
