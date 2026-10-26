# v0.1 evaluation replay

## Incremental account engine

Increment 3 adds explicit `evaluation`/`funded` account types and `eod_trailing` policy. The floor updates only at an observed close using `max(old_floor, min(floor_cap, highest_completed_balance - trailing_distance))`. It uses the final session balance, not the intraday peak. Evaluation passing requires positive profit meeting the target and strict consistency `best_winning_day <= consistency_limit * total_net_profit`, checked only at close. Funded accounts have no evaluation target/consistency and count completed days meeting the explicit net-profit threshold. Qualifying days alone do not establish payout eligibility.

`finish_data()` seals further input, is idempotent, preserves passed/breached outcomes, and reports active accounts as unfinished without closing an unobserved final session. Snapshots expose the current floor, highest completed balance, best completed winning day, qualifying-day count, and data-end outcome. Unsupported policies and missing stage/trailing settings are rejected. The fixed-floor development API remains available for earlier examples.

See synthetic evaluation passing, funded qualifying days, and an unfinished final session:

```powershell
python Strategies/MyStarterPlaybook/simulator/demo_session_rules.py
```

All **46 tests pass**: nine accounting, 12 loss-limit, 12 session-rule, and 13 legacy replay tests. Next is the validated historical adapter. The strict consistency and EOD floor formula are explicit development policies; provider nuances remain unresolved, and the full research draft remains non-executable. No historical account-engine run or payout study has been performed.

Increment 2 adds immutable `AccountRules`/`SessionClose` and `AccountEngine`. Explicit development rules select starting capital, a **fixed** loss floor, and an optional net-session DLL. Equality at the floor breaches, with hard breach taking priority over DLL. Equality at minus the DLL locks that account; later trades are skipped without P&L or commissions. Only an observed close followed by a new session resets the lock. Breached accounts cannot be revived. No-trade sessions can close explicitly; duplicate/closed-session and out-of-order input is rejected. Audit events include account ID, timestamp, and source order.

For visible loss-limit transitions, run from the repository root:

```powershell
python Strategies/MyStarterPlaybook/simulator/demo_loss_limits.py
```

This synthetic demo shows DLL lockout, a skipped profit, next-session recovery, and permanent breach using the fixed-floor policy. Use the session-rule demo above for EOD trailing/evaluation behavior.

`account_engine.py` contains the first tested increment: `CompletedTrade`, `AccountLedger`, and immutable `TradeApplied` accounting events. Inputs use timezone-aware datetimes, explicit session IDs/source order, one-contract trades, and finite Decimal gross P&L/commissions. The caller must establish flat-to-flat inventory. Snapshots are JSON-serializable; money and ratios are decimal strings, with unavailable ratios represented by `null`.

The ledger starts each account at its supplied capital, deducts each trade's commission once, and tracks net wins/losses, session totals, and closed-trade balance drawdown. It rejects duplicates, overlapping positions, and out-of-order input before mutating state. The standalone ledger includes every supplied trade; `AccountEngine` decides which trades to apply. See the [delivery checkpoints](../../../docs/plans/ACCOUNT_ENGINE_PLAN.md#incremental-delivery-checkpoints).

Accounting checkpoint: net trades `+100, -50, 0, +150` from gross `+101, -49, +1, +151`, each with $1 commission, turn $25,000 into $25,200. Average win is $125, average loss is -$50, win rate is 50% including the breakeven trade, and maximum closed-trade drawdown is $50.

For a readable trade-by-trade demonstration with synthetic inputs, run from the repository root:

```powershell
python Strategies/MyStarterPlaybook/simulator/demo_accounting.py
```

This prints each trade's gross P&L, commission, net P&L, and resulting balance, then the final statistics and a duplicate-trade rejection. It uses the actual ledger and writes no files. These are sample trades, not historical strategy performance.

For automated accounting checks, run:

```powershell
python -m unittest discover -s Strategies/MyStarterPlaybook/simulator/tests -p test_account_engine.py -v
```

The existing replay commands below retain their original behavior.

Python 3.10+; standard library only. This prototype validates the first strategy iteration and replays one evaluation attempt from the beginning of a selected run. NinjaScript and original exports are left unchanged.

## Planned lifecycle study — October 26, 2026

The active target is the [50-purchase FLEX lifecycle plan](../../../docs/plans/SIM_PROP_PLAN.md): DLL ON at $600, 50% evaluation consistency, $43.20 purchases, funded accounts, payouts, and net cash accounting. See [next steps](../../../docs/plans/SIM_PROP_PLAN.md#current-status-and-next-step) for the remaining execution specification.

Runnable commands below still describe the existing DLL-off/40% single-evaluation prototype. The study CLI is not implemented. Its [research draft](../../../rules/lucidflex_25k_dll_on_50pct_study_draft.json) cannot be passed to `--config`. Independent start-date batches are deferred.

The user approved a simpler model for the planned study: use completed-trade net results, check loss limits after each closed trade, and update the trailing floor at session end. Intrabar/tick data is not required. Reports will note that open-trade limit touches are excluded. This does not change the existing prototype's observation-based behavior below.

From the repository root:

```powershell
python Strategies/MyStarterPlaybook/simulator/replay.py replay `
  --run Strategies/MyStarterPlaybook/logs/logging-on/0.1 `
  --analyzer-trades Strategies/MyStarterPlaybook/logs/logging-on/0.1/analyzer-trades.csv `
  --analyzer-summary Strategies/MyStarterPlaybook/logs/logging-on/0.1/analyzer-summary.csv
```

Replace `replay` with `validate` to produce only validation/provenance reports. A failed check returns a nonzero exit code and prevents simulation. The terminal prints the output directory.

## Outputs and versions

Every invocation creates a new folder under `simulation-results/v0.1/<UTC timestamp>_<unique suffix>/`. Optional `--out <new-directory>` selects another destination; existing directories are rejected. Reports never overwrite input data or past results.

- `validation.json`: counts, gross P&L reconciliation, daily gross/net totals, and full-run assumed costs.
- `provenance.json`: input paths and SHA-256 hashes, source run ID, strategy version, simulator revision/code hash, rule snapshot hash, and resolved scenario settings.
- `result.json`: single-attempt outcome, observed balance/equity, floor, and stopping timestamp.
- `events.csv`: observed fills, completed sessions, floor updates, and terminal decision.
- `report.md`: readable findings and scenario assumptions.

Full-run validation P&L and the single-attempt stopping balance are different measures. The attempt stops at its first sampled breach or pass. Later strategy results do not revive a breached account.

## Validation scope

The validator checks finalized/usable metadata; expected schemas; run/instrument identities; event sequence and timestamp ordering; actual execution inventory, entry basis, and realized P&L; unique fill/trade associations; segment P&L; every Analyzer trade's direction, quantity, prices, times, names, and profit; summary totals; equity state at each observation; daily gross reconciliation; valid bars; counts; and observed range.

Supported input is MNQ at $2/point, historical unit fills, one position contract at most, no layering/reversal fills, no overnight holdings, and flat initial/final inventory. Analyzer timestamps must use the logger source wall clock, in the exported US date format, at second precision. The prototype currently reconciles zero-cost Analyzer reference exports only; it rejects cost-bearing exports rather than guessing fee semantics. It requires every fill to have a reliable unique ID and an associated execution equity observation. Unsupported data fails validation.

The fixed replay commission replaces logged costs using gross accounting: `$0.50 × filled contracts` per execution. It never subtracts both logged net costs and the scenario commission. The actual input's commission mode is Unknown; the assumed rate is not a measured result. Partial fills, layering, and other unsupported inventory cases must be added with validation before using those runs.

## Provisional rule scenario

Default configuration: [configs/lucidflex_25k_provisional.json](configs/lucidflex_25k_provisional.json). Use `--config` for an explicit alternative file within the supported model.

This is a historical scenario based on the dated October 22 reference, not a claim about current provider terms. It models $25,000 starting balance, $1,250 target, $1,000 EOD trailing loss allowance capped at a $25,100 floor, DLL off, and strict 40% consistency. One original MNQ contract is used without quantity multiplication.

Scenario choices that still require provider confirmation:

- Daily reset at 18:00 on the recorded Eastern wall clock; embedded offsets handle the input's DST. No independent provider holiday calendar is implemented. Exchange `trading_day` is validated as a date but is not substituted for the configured reset day.
- At the next observed session, the prior session's final flat balance updates the highest EOD balance and loss floor. The floor never decreases; equality breaches.
- Breach checks use net marked equity at every available equity observation, including fill observations, and stop immediately. Recorded marks are approximate Last/bar-close marks, not executable bid/ask liquidation quotes.
- Pass eligibility is checked at completed session end while flat: net profit meets target and largest winning session / total net profit is at most 40%. No consistency cushion is guessed.
- The last session is left unclosed if the next rollover is absent. Data exhaustion without pass/breach is `incomplete`, not failure.

No historical Last ticks were captured in the current run. An unobserved intrabar breach may have occurred before the reported stop. A sampled pass would not prove survival. No synthetic liquidation, exit cost, or broker balance is invented at breach; an open position at stop is reported as such.

Purchase fees are unknown, so net cash profitability is unavailable. DLL-on, funded stages, payouts, resets/repeated attempts, alternate start dates, position scaling, inactivity policies, and a complete provider rulebook are outside this first implementation.

## Tests

```powershell
python -m unittest discover -s Strategies/MyStarterPlaybook/simulator/tests -v
```

Boundary tests cover equality breaches, entry-side cost effects, EOD-only ratcheting, cap behavior, consistency, final-session censoring, stop-on-breach behavior, overnight rejection, offset/timestamp handling, invalid inputs, and single deduction of costs. The full real-run invocation above separately exercises reconciliation against Analyzer.
