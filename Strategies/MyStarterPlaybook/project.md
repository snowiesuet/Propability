# FairPriceStrategy — Prop Firm Backtesting Project

Last updated: October 25, 2026 (America/New_York)
Platform: NinjaTrader 8 / C#; simulator: Python 3.10+ (standard library)
Status: v0.1 input validation and single-evaluation Python replay implemented; broader acceptance and account lifecycle pending

## Objective

Evaluate how the existing FairPriceStrategy performs through repeated prop firm evaluations and funded-account cycles, including failures, fees, drawdown limits, and payouts. The intended outcome is a reproducible estimate of account survival and net profitability across attempts, rather than an assessment based only on Strategy Analyzer profit.

The requirements source is [objective.md](../../objective.md). It calls the strategy **Cont & Rev** and the provider **Lucify**. The implemented strategy class and NinjaTrader display name are `NYOpenFairPriceStrategy`; FairPriceStrategy is the project shorthand. The available dated provider reference is **Lucid Trading / LucidFlex $25K**. Keep these names explicit and confirm the intended provider before treating a simulation configuration as authoritative.

## Scope and priorities

The current work instruments the existing strategy and prepares its data for a separate Python simulator. Preserve its entry logic, exit logic, indicators, risk settings, calculation mode, and order execution behavior. Strategy optimization or trading changes require a separate scope and baseline.

Priorities from objective.md:

1. Data correctness.
2. Preservation of existing strategy behavior.
3. Logging performance.

Prop firm rules, starting account balances, fees, resets, and payout calculations belong in Python configuration and simulation code. Do not hardcode them into NinjaScript or equate strategy P&L with a prop firm account balance.

## Current strategy baseline

Source: [NYOpenFairPriceStrategy.cs](NYOpenFairPriceStrategy.cs).

- Fair price is anchored to the configured opening bar's open, defaulting to 9:30 in the configured NinjaTrader time context.
- Opening-direction continuation uses structure breaks or displacement during the initial window; later entries seek reversion toward fair price.
- Defaults: continuation window 15 minutes, reversion cutoff 90 minutes from the configured open, maximum four entry submissions per session, layering disabled.
- Managed orders, `Calculate.OnBarClose`, `EntryHandling.UniqueEntries`, and `EntriesPerDirection = 10`.
- Entry submissions are one contract each. Continuation requires flat; optional reversion layering can create more complex inventory and reversals.
- Signal-specific stops and targets are set before entry. ATR(14) selects stop/target distances; reversion can target fair price instead of a fixed distance.
- Session-close exits are enabled with a 30-second setting. No explicit trailing-stop or scale-out logic exists.
- NQ one-minute is a source recommendation, not an enforced instrument/timeframe. The saved run uses MNQ one-minute data.

The earlier ATRManagerV1 prototype is outside this project's active scope. Its stop-submission redesign and trailing-stop roadmap do not define FairPriceStrategy's next steps.

## Project files

| Path | Purpose |
| --- | --- |
| `../../objective.md` | Instrumentation requirements and acceptance criteria |
| `roadmap.md` | Progress checklist and remaining milestones |
| `NYOpenFairPriceStrategy.cs` | Existing continuation/reversion strategy with logging integration |
| `ContRevCsvLogger.cs` | Independent fill ledger and structured output |
| `LOGGING.md` | Current schemas, accounting conventions, setup, and limitations |
| `tests/` | C# logger fixtures, Python validation, and trading-body integrity checks |
| `logs/logging-on/0.1/` | Saved historical baseline output |
| `../../rules/lucidflex_25k_2026-10-22.md` | Dated provider rules, comparison settings, and unresolved details |
| `ATRManagerV1.cs` | Earlier prototype; outside current scope |

## Current progress and gaps

The instrumentation foundation exists, but objective.md's full acceptance criteria are not yet met.

| Requirement | Current state | Remaining work |
| --- | --- | --- |
| Execution logging | `executions.csv` records actual fills, identifiers, quantities, prices, position state, and accounting quality | Reconcile a real run against Analyzer, including partial fills and reversals |
| Completed trade segments | `trades.csv` matches closed entry-fill quantities and allocates known costs | Validate platform totals and document matching differences per run |
| Equity observations | `equity.csv` records strategy equity changes at bar closes, executions, and available Last ticks | Map to the requested account snapshot fields in Python; add or derive explicit daily/session reset state |
| Primary price history | `bars.csv` includes warmup and flat periods | Use OHLC only with documented ordering assumptions or bounds |
| Order lifecycle | Not implemented; executions do not describe unfilled orders | Add `orders.csv` for submissions, state changes, cancellations, and rejections |
| Session summaries | `sessions.csv` not implemented | Produce session summaries with explicit boundaries and sampling quality |
| Run metadata | `run_metadata.json` records parameters, runtime settings, instrument/session details, completeness, and final inventory | Audit against every requested field; retain unavailable values explicitly |
| Validation | Python reconciles all 547 current trades, summary totals, inventory, sampled equity, and daily gross accounting | Complete platform acceptance and measured-cost validation |
| Prop firm simulator | Provisional one-contract evaluation replay implemented | Resolve assumptions; add repeated attempts, funded accounts, fees, and payouts |

The current `equity.csv` schema intentionally reports strategy P&L/equity changes rather than inventing an account balance. It does not yet fulfill the complete `account_equity.csv` requirement in objective.md. Any mapping, derived fields, or schema changes must be documented and versioned.

One trade row represents a closed entry-fill quantity segment, not necessarily one order or one complete flat-to-flat position. Execution and trade realized totals are alternate views of the same P&L and must never be added together.

## Saved baseline: logs/0.1

The saved run metadata reports:

| Item | Value |
| --- | --- |
| Instrument / interval | MNQ DEC26 / 1 minute |
| Observed period | January 1, 2026 at 18:01 through October 23, 2026 at 16:59, configured Eastern time |
| Trading-hours template | CME US Index Futures ETH |
| Primary bars | 260,738 |
| Execution records | 1,094 |
| Closed trade segments | 547 |
| Final gross realized P&L | -$2,432.50 |
| Final inventory | Flat |
| Completion / accounting | Finalized, usable, accounting complete |
| Commissions | Unknown; commission accounting incomplete |
| Historical Last ticks | None |

These are recorded baseline results, not a prop firm pass/fail result. Gross P&L excludes unknown commissions. `usable` indicates finalized, reconstructable logger accounting; it does not certify full compliance with objective.md or exact intrabar account survival.

## Data correctness and simulation limits

- Use actual fills and preserve partial fills, multiple entries, partial exits, and reversals. Never infer fills from order submissions.
- Distinguish unavailable values from genuine zero. Flag unknown commissions, ambiguous timestamps, and accounting failures.
- Keep instrument currency, point value, quantity, and commission basis explicit. Deduct costs exactly once.
- Preserve run isolation and stable identifiers. Record final open inventory without synthesizing closing fills.
- Use only information available at each observation; do not assign a bar's high or low to an entry whose intrabar timing is unknown.
- The saved run contains bar-close equity and fill observations, but no historical Last ticks. It cannot prove the ordering of every intrabar drawdown breach.
- Sampled excursions and equity extrema must be labeled as sampled. Investigate replay/tick observations without changing trading behavior; otherwise report conservative bounds or explicit uncertainty.
- Exchange trading dates and a prop firm's daily-reset boundary may differ. Model the provider's timezone, session calendar, and reset rules separately.
- Quantity scaling assumes unchanged fills and prices unless a more realistic execution model is supplied. It does not establish that larger orders would fill identically.

## Planned prop firm comparison

Use the dated [LucidFlex reference](../../rules/lucidflex_25k_2026-10-22.md) as an input snapshot, with its unknowns preserved. Do not silently replace it when terms change; create a new dated snapshot.

Current comparison intent recorded there:

- Compare DLL on/off and 40%/50% evaluation consistency: four configurations.
- Compare MNQ sizing from 1–10 micros per entry.
- Apply a personal account-purchase budget of at most $500 per month.
- For replay of the existing gross logs, use the reference assumption of $0.50 per filled MNQ contract per side, without double-counting any logged costs.

The simulator should model repeated evaluation attempts, pass/fail outcomes, funded progression, daily loss locks, static/trailing drawdown, consistency, qualifying days, payout eligibility, withdrawals, fees, profit splits, and account breaches.

Before authoritative comparisons, resolve provider identity, actual checkout costs, DLL amount and calculation basis, consistency cushion/rounding, intraday drawdown enforcement, reset/calendar rules, evaluation-to-funded transitions, and payout timing. Budget carryover, repurchases, parallel accounts, and reinvestment also need explicit simulation policies. Unresolved inputs must be reported as unknowns or named scenarios.

## Next milestones

1. **Validate the existing NinjaTrader integration.** Compile both source files in NinjaTrader, then compare the original baseline, logging disabled, and logging enabled with identical data and settings. Check fills, timestamps, quantities, inventory, and results, including layering, session closes, and partial fills where available.
2. **Close the instrumentation gaps.** Add order lifecycle output, explicit session summaries/reset state, the documented account-equity mapping, and a metadata requirements audit while preserving trading behavior.
3. **Produce a reconciled baseline.** Generate a commission-aware run and a per-run report comparing Analyzer totals, execution/trade accounting, fees, daily totals, counts, and ending inventory. Flag discrepancies rather than adjusting them away.
4. **Define simulator configuration.** Resolve the provider/rule inputs and account lifecycle policies; separate verified rules from scenario assumptions.
5. **Implement Python replay.** Start with deterministic accounting and one configured account lifecycle, then add repeated attempts, budget constraints, sizing comparisons, and payout cycles.
6. **Report outcomes and uncertainty.** Compare pass rates across replay start dates, breach reasons, time to pass/payout, attempt costs, payouts received, and net cash results. Distinguish historical replay outcomes from forecasts and label intrabar uncertainty.

## Validation and completion criteria

Run the current local checks from the repository root:

```powershell
powershell -File Strategies/MyStarterPlaybook/tests/run.ps1
```

The runner compiles the standalone C# logger, validates fixture CSV/JSON accounting, and checks preserved trading-body hashes. pandas ingestion is checked when pandas is available. Optional installed-assembly compilation and platform acceptance procedures are documented in [LOGGING.md](LOGGING.md).

Local checks were rerun on October 25, 2026: accounting/CSV checks and trading-body hashes passed; pandas was unavailable. This does not replace NinjaTrader runtime validation.

Instrumentation is complete when the strategy compiles, trading behavior is preserved, all required outputs or explicitly agreed schema mappings exist, identifiers and session boundaries reconcile, a per-run Analyzer comparison is available, and remaining sampling limitations are documented.

The broader project is complete when a separate configurable Python simulator can consume validated runs and reproduce evaluation/funded-account outcomes, fees, breaches, payouts, and net cash results across repeated attempts, with traceable rules and explicit uncertainty.

## Python prototype — October 25 update

[simulator/README.md](simulator/README.md) documents the CLI, supported inputs, assumptions, and outputs. The current 547-trade run reconciles to Analyzer gross results. Full-run fixed commissions of $547 produce modeled net P&L of -$2,979.50; these costs are an assumption, not measured platform commissions.

The one-contract DLL-off/strict-40% scenario reports an observed equity breach on January 21, 2026 at 10:16 Eastern: $24,265.50 equity versus a $24,266.00 floor. Missing intrabar observations may hide an earlier breach. No liquidation or purchase fee is invented. This is one attempt from the input start, not a pass-rate estimate.

Results: [first validated replay](simulation-results/v0.1/20261025T202249Z_3fbf4a08/report.md). Reports record input/configuration/rule/code hashes and the source run ID. Thirteen tests cover reconciliation, corrupted inputs, cost accounting, and replay boundaries. Original logs and strategy sources were not changed. Remaining platform acceptance, expanded logging, authoritative rules, funded accounts, payouts, and repeated attempts remain open.
