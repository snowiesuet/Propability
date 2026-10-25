# FairPriceStrategy Roadmap

Updated: October 25, 2026. **Python prototype is running; remaining platform acceptance stays open.**

Goal: find out how FairPriceStrategy performs through prop firm evaluations, funded accounts, fees, and payouts.

- [x] **Phase 1 — Build the foundation.** Strategy, CSV logger, local checks, and historical data are available.
- [ ] **Phase 2 — Verify trading behavior.** Layering-disabled ON/OFF trades match; layering and remaining platform checks are pending.
- [ ] **Phase 3 — Complete the data.** Fill the logging gaps and document data limits.
- [ ] **Phase 4 — Validate a baseline.** v0.1 gross accounting and all 547 trades reconcile with Analyzer; measured costs and full acceptance remain open.
- [ ] **Phase 5 — Define prop firm scenarios.** One provisional DLL-off/40% scenario exists; unresolved provider rules and fees remain open.
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
- [ ] Extend replay to alternate start dates and repeated evaluations, then funded accounts/payouts.

**Next move:** review the [first replay report](simulation-results/v0.1/20261025T202249Z_3fbf4a08/report.md) and its assumptions before extending the account lifecycle. Missing intrabar observations may hide an earlier breach.

Usage: [simulator/README.md](simulator/README.md). Details: [project.md](project.md), [detailed checklist](roadmap-detailed.md), and [VERSIONING.md](VERSIONING.md).
