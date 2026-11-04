# FairPriceStrategy Roadmap

Paths in code examples and data-folder references are relative to `Strategies/MyStarterPlaybook/` unless stated otherwise. Document links resolve from this file.

Updated: November 3, 2026. **Lifecycle prototype is running; provider-rule and platform acceptance remain open.**

Account-engine checkpoint: increments 1–4 complete. The lifecycle runner connects validated historical data to sequential attempts, funded accounts, payouts, the cash ledger, and the initial live stage. A first full-history run used all 547 trades but supported 10 purchases; it ended with 2 passes, 7 breaches, 1 unfinished evaluation, and 2 funded accounts unfinished. Hand-calculated/synthetic lifecycle and 50-purchase-cap fixtures and all 49 simulator tests pass. Provider-rule completion and a longer history for 50 purchases remain open. See the [lifecycle plan](../../../docs/plans/SIM_PROP_PLAN.md).

Goal: find out how FairPriceStrategy performs through prop firm evaluations, funded accounts, fees, and payouts.

Primary output: a concise [50-account scorecard](../../../docs/plans/SIM_PROP_PLAN.md#primary-goal-and-scorecard) showing trade win rate, average win/loss, evaluation pass/breach counts and rates, funded accounts, payout dollars, costs, and net cash profit. The user's example is a report-format reference, not simulation results. Use the agreed sequential purchases and completed-trade model.

- [x] **Phase 1 — Build the foundation.** Strategy, CSV logger, local checks, and historical data are available.
- [ ] **Phase 2 — Verify trading behavior.** Layering-disabled ON/OFF trades match; layering and remaining platform checks are pending.
- [ ] **Phase 3 — Complete the data.** Fill the logging gaps and document data limits.
- [ ] **Phase 4 — Validate a baseline.** v0.1 gross accounting and all 547 trades reconcile with Analyzer; measured costs and full acceptance remain open.
- [ ] **Phase 5 — Define prop firm scenarios.** FLEX DLL-on/50% settings, $43.20 purchases, research, and draft study configuration are saved; execution gaps remain.
- [x] **Phase 6 — Build the Python simulator.** Initial lifecycle coordinator and historical report implemented; rule-complete acceptance remains open.
- [ ] **Phase 7 — Compare results.** Accept the scorecard and later compare sizing/account options using survival, payouts, costs, and net cash results.

## Current progress

- [x] Strategy compiles and exports CSV files.
- [x] Logging ON/OFF matches across all 547 trades with layering disabled.
- [x] Preserve v0.1 source snapshot and index input runs by run ID.
- [x] Validate the saved logger data against every Analyzer trade, summary totals, and sampled equity accounting.
- [x] Build/test one-contract evaluation replay with explicit costs, EOD drawdown, consistency, and an event history.
- [x] Save the first provisional result: observed breach January 21, 2026 at 10:16 Eastern.
- [ ] Verify remaining platform cases, including layering, and resolve authoritative rule/cost inputs.
- [x] Select the 50-purchase FLEX lifecycle study and save screenshot inputs, official research, and draft configuration.
- [ ] Finish the execution specification and validate required rules/policies before strict replay.
- [x] Implement initial independent accounts, sequential purchases, funded progression, payouts, cash ledger, and Stat / Value report.
- [x] Reconcile first payout, payout-5 live transition, bonus receipt, and cash ledger against hand-calculated/synthetic fixtures.
- [ ] Resolve or explicitly accept remaining DLL, consistency, qualifying-day, and fee limitations.

**Next milestone: run the accepted lifecycle prototype on a longer validated history.** The user selected the start date, withdrawal policy, capacity handling, and payout-5 live transition. Synthetic fixtures cover payout and live behavior; the actual historical window has no payouts and supports only 10 purchases. Keep the remaining DLL, qualifying-day, fee, and live-payout gaps visible. See [current next steps](../../../docs/plans/SIM_PROP_PLAN.md#current-status-and-next-step).

Selected study: FLEX $25K, DLL ON at $600, 50% evaluation consistency, no funded consistency, $43.20 per purchase ($2,160 for 50), free activation, one MNQ per account. Keep one evaluation active and funded accounts trading independently; the study intentionally excludes household capacity limits by user choice. No monthly budget constraint; resets are not purchased.

The lifecycle prototype includes funded payouts and known evaluation purchase costs. Count only modeled bank receipts minus external costs as net cash profit; do not count remaining account balances or pending payouts. Ordinary live payouts remain unmodeled. The existing executable and saved legacy results still describe the separate provisional DLL-off/40% replay.

Implementation phases: confirm execution inputs; build the account engine; implement 50-attempt lifecycle/payouts/cash ledger; validate reports against fixtures and historical data. The initial runner and synthetic fixture acceptance are delivered; full historical and platform acceptance remain open. Start-date batches, sizing comparisons, and budget controls are later work.

Usage: [simulator/README.md](../simulator/README.md). Details: [project.md](project.md), [detailed checklist](roadmap-detailed.md), and [VERSIONING.md](VERSIONING.md).
