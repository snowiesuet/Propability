# FairPriceStrategy Roadmap

Paths in code examples and data-folder references are relative to `Strategies/MyStarterPlaybook/` unless stated otherwise. Document links resolve from this file.

Updated: October 26, 2026. **Python prototype is running; remaining platform acceptance stays open.**

Account-engine checkpoint: increments 1–3 complete, with 33 account tests and all 13 legacy tests passing. Accounting, loss limits, EOD trailing/cap, strict evaluation passing, funded qualifying days, and unfinished-data handling are tested on synthetic fixtures. Next connect validated historical data and reconcile both account types, including skipped trades. See the [incremental plan](../../../docs/plans/ACCOUNT_ENGINE_PLAN.md#incremental-delivery-checkpoints). The 50-account lifecycle and payouts remain pending.

Goal: find out how FairPriceStrategy performs through prop firm evaluations, funded accounts, fees, and payouts.

Primary output: a concise [50-account scorecard](../../../docs/plans/SIM_PROP_PLAN.md#primary-goal-and-scorecard) showing trade win rate, average win/loss, evaluation pass/breach counts and rates, funded accounts, payout dollars, costs, and net cash profit. The user's example is a report-format reference, not simulation results. Use the agreed sequential purchases and completed-trade model.

- [x] **Phase 1 — Build the foundation.** Strategy, CSV logger, local checks, and historical data are available.
- [ ] **Phase 2 — Verify trading behavior.** Layering-disabled ON/OFF trades match; layering and remaining platform checks are pending.
- [ ] **Phase 3 — Complete the data.** Fill the logging gaps and document data limits.
- [ ] **Phase 4 — Validate a baseline.** v0.1 gross accounting and all 547 trades reconcile with Analyzer; measured costs and full acceptance remain open.
- [ ] **Phase 5 — Define prop firm scenarios.** FLEX DLL-on/50% settings, $43.20 purchases, research, and draft study configuration are saved; execution gaps remain.
- [ ] **Phase 6 — Build the Python simulator.** Single-evaluation prototype works; funded accounts, payouts, and repeated attempts remain.
- [ ] **Phase 7 — Compare results.** Compare sizing and account options using survival, payouts, costs, and net cash results.

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
- [ ] Implement independent accounts, sequential purchases, funded progression, payouts, cash ledger, and historical acceptance.

**Next milestone: finish the execution specification for the 50-purchase lifecycle study.** Resolve remaining completed-trade rules, choose withdrawal timing/amount and start date, and define funded-slot/live-review handling. The user approved closed-trade loss checks and session-end floor updates; intrabar data is deferred and does not block implementation. See [current next steps](../../../docs/plans/SIM_PROP_PLAN.md#current-status-and-next-step).

Selected study: FLEX $25K, DLL ON at $600, 50% evaluation consistency, no funded consistency, $43.20 per purchase ($2,160 for 50), free activation, one MNQ per account. Keep one evaluation active and funded accounts trading independently, subject to the five-funded/ten-total household limits. No monthly budget constraint; resets are not purchased.

The first release includes payouts and external costs. Count only modeled bank receipts minus external costs as net cash profit; do not count remaining account balances or pending payouts. No lifecycle study has run. The existing executable and saved results still describe the separate provisional DLL-off/40% replay.

Implementation phases: confirm execution inputs; build the account engine; implement 50-attempt lifecycle/payouts/cash ledger; validate reports against fixtures and historical data. Platform acceptance remains open alongside this work. Start-date batches, sizing comparisons, and budget controls are later work.

Usage: [simulator/README.md](../simulator/README.md). Details: [project.md](project.md), [detailed checklist](roadmap-detailed.md), and [VERSIONING.md](VERSIONING.md).
