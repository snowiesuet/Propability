# Cont & Rev CSV logging

Copy **both** `NYOpenFairPriceStrategy.cs` and `ContRevCsvLogger.cs` into the NinjaTrader 8 custom Strategies directory, then compile in the NinjaScript Editor. Do not copy the `tests` directory. The strategy's class and displayed name remain `NYOpenFairPriceStrategy`.

Enable **CSV Logging → Enable CSV Logging** in the strategy parameters. The default is disabled. A blank output root uses `NinjaTrader.Core.Globals.UserDataDir/ContRevBacktestLogs`. Every instance/optimization iteration gets its own timestamp-and-GUID run directory. Logging starts on the first primary-bar callback, before all original trading/warmup guards, and finalizes in Terminated. Initialization waits for strategy Position to be available instead of reading it in DataLoaded. No-bar runs produce no files. Files remain buffered until the next primary bar or termination. Performance overhead can affect live timing even though no trading calculations or order calls were changed.

The NinjaScript Output window prints `Cont & Rev CSV logging started: <run folder>` on successful initialization. Failures print the failing logging stage, strategy state, and complete exception/stack trace; logging is disabled without interrupting trading.

## Existing strategy inspection

The strategy uses managed entries, `OnBarClose`, `EntryHandling.UniqueEntries`, and `EntriesPerDirection=10`. It anchors fair value at the configured opening bar, takes opening-direction continuation on a structure break or displacement, and subsequently takes reversion toward fair value. Entry submissions are one contract each. Continuation requires flat; reversion permits layering when enabled, including opposite-direction submissions. Entry counters count submissions, not fills, and are left unchanged.

Every entry sets a signal-specific stop and profit target before submitting the entry. ATR(14) controls stop/target distances: below 7 uses 16.5/24.75 points, above 20 uses 50/75, otherwise configured defaults 25/37.5; invalid ATR falls back to those configured parameters. Reversion targets can instead use the distance to fair price. Session-close exits are enabled with a 30-second setting. No explicit scale-out or trailing-stop logic exists. Platform partial fills and partial closes must nevertheless be handled individually.

NQ one-minute is a source comment recommendation, not an enforced instrument or interval. Session template, instrument, fill settings, and timezone are runtime inputs. The original source has chart drawings but no execution, position, order-update, realized/unrealized P&L accounting, or structured output. The added logger owns its own accounting state; it never changes the strategy Position or submits, cancels, or updates orders.

Actual fills, prices, quantities, and callback identities are reliable observations. Optional order fields and account names can be absent. Orderless execution side comes from the execution's reported Long/Short side, with that provenance flagged. There is no Filled-state filter. Unknown direction invalidates subsequent accounting while raw fills continue to be written. No order-status history is exported; an unfilled/cancelled order is not an execution.

## Encoding and common fields

Files use UTF-8 without BOM, comma delimiters, escaped double quotes/newlines, invariant decimal points, and a single header. An empty field means unavailable; `0` is a genuine measured/calculated zero. Strings such as order and execution IDs must be read as strings. `run_id` joins files. Instrument names include the contract. All money is in instrument currency using the instrument point value; there is no account-currency conversion.

`timestamp`, `entry_timestamp`, and `exit_timestamp` retain callback wall time in NinjaTrader's configured timezone with seven fractional digits and an offset when unambiguous. Ambiguous/invalid DST times omit the offset and are flagged `TimezoneUnresolved`; do not invent an instant for them. The timezone identifier is in metadata. Sequence numbers encode logger observation order, not exchange causality or a guarantee of timestamp monotonicity. Trade segments share their closing execution's sequence; execution and equity rows have distinct increasing sequences.

`trading_day` is the exchange trading date returned by a dedicated `SessionIterator(BarsArray[0]).GetTradingDay(time)`, not the local calendar date or a Lucify daily-reset rule. For example, an evening timestamp can belong to the next trading day. The simulator must apply Lucify's reset timezone separately when supplied. Metadata records the trading-hours template and its timezone.

## CSV schemas

The header in each file is the authoritative column order. These grouped descriptions cover every column.

| File | Columns and meaning |
| --- | --- |
| executions.csv | `run_id`, `strategy_name`, `instrument`, `account_name`; `execution_id`, `order_id`, `order_name`; `timestamp`, `trading_day`; `market_position` (reported execution side, not after-fill position), `execution_side` (order action, or inferred Buy/Sell), `execution_quantity`, `execution_price`; `commission` (this fill's cost), `realized_pnl` (this fill's gross incremental closed P&L); `position_quantity_after_execution` (absolute), `average_position_price_after_execution` (blank when flat); `event_sequence`, `position_id`, `signed_position_quantity_after_execution`; `execution_phase`, `commission_source`, `commission_status`, `data_quality`, `entry_signal`, `previous_position_id`. |
| trades.csv | `run_id`, unique `trade_id`, `instrument`, `direction`; `entry_timestamp`, `exit_timestamp`, `entry_price`, `exit_price`, closed `quantity`; `gross_realized_pnl`, allocated `commissions`, `net_realized_pnl`; `maximum_favorable_excursion`, `maximum_adverse_excursion` (nonnegative currency magnitudes); `exit_reason`, `entry_signal`, `trading_day` (exit day); `position_id`, `entry_execution_id`, `exit_execution_id`, `entry_order_id`, `exit_order_id`, `entry_trading_day`; `commission_source`, `commission_status`, `excursion_sampling_quality`, `raw_exit_name`, `event_sequence`. |
| equity.csv | `run_id`, `instrument`, `timestamp`, `trading_day`, `event_sequence`; `observation_source` (BarClose, Execution, Last), `execution_phase`; `signed_position_quantity`, `average_position_price`, `mark_price`; `cumulative_gross_realized_pnl`, `cumulative_commissions`, `cumulative_net_realized_pnl`, `unrealized_pnl`, `gross_equity_change`, `net_equity_change`; `data_quality`, `position_id`. |
| bars.csv | `run_id`, `instrument`, `timestamp`, `trading_day`, `event_sequence`, `execution_phase`; `open`, `high`, `low`, `close`, `volume`, `data_quality`. All available primary bars are exported, including warmup and flat/out-of-window periods. |

`position_id` identifies a continuous directional position, ending at flat or reversal. On a reversal execution the ID identifies the newly opened position and `previous_position_id` identifies the closed position. On a flat-closing execution `position_id` identifies the position just closed. A pure opening execution has zero gross realized P&L. Unknown accounting produces blanks, never substitute zeros.

## Matching, commissions, and excursions

One trade row is one closed entry-fill quantity segment, not necessarily a whole order or flat-to-flat lifecycle. Match an exit's `FromEntrySignal` first, FIFO within that signal. Unassociated exits use global FIFO. An association with no remaining matching lot falls back to global FIFO and flags `SignalMatchFallbackFIFO` on the execution. This independent matching convention can differ from NinjaTrader's performance presentation; compare total P&L and inventory as well as the documented matching policy.

Reversals close available opposing lots and open the remainder at the actual execution price, with proportional commission allocation and a new position ID. A single fill stays one execution row. Missing execution IDs are retained and flagged; reliable IDs are deduplicated within phase/instrument/account/order scope. Historical and realtime IDs cannot suppress one another. Logger state is serialized by the strategy's private gate; the standalone component requires serialized calls.

Commission settings affect logging only:

- **Unknown** (default): commission/net fields are blank after an execution with unknown cost. Gross results remain available.
- **Platform**: explicitly asserts that NinjaTrader's execution commission settings are configured and trustworthy. Snapshot the execution's commission once; zero is known zero. Missing, negative, or nonfinite commission is unknown. Later broker adjustments are not reconciled; use fixed mode or postprocess separately if needed.
- **FixedPerContractPerSide**: use the configured nonnegative rate times actual fill quantity. Explicit zero is known zero. This is the logging-only fallback when platform costs are not confirmed; mode selection is explicit, with no heuristic interpretation of platform zeros.

Costs are allocated by filled quantity across segments and any still-open quantity. Trade net = trade gross − allocated entry/exit costs. Equity net also deducts entry costs of positions still open. **Executions and trades are alternate views of the same realized P&L: never sum both files' realized totals.** Final metadata lists remaining lots and unallocated entry costs. Termination never synthesizes an exit.

Excursions use only observed fill prices, primary bar closes, and available Last ticks while the lot is open, including its closing fill. They are sampled approximations; genuine observed zero is possible. Bar highs/lows are never assigned to lots because their ordering relative to fills is unknown. OHLC is exported separately for conservative bound calculations. Last-price marks do not represent executable bid/ask liquidation prices.

## Run validity and simulator limits

`run_metadata.json` records schema version, configured strategy parameters, available runtime/fill settings (unavailable properties are null), instrument specifications, source/session timezones, observed time range, counts, final open inventory, accounting/cost completeness, and sampling coverage. Parameter/runtime values are stored as invariant strings. Initial nonflat strategy inventory is unsupported and disables logging rather than inventing its entry basis.

Only accept `completion_status == "Finalized"` and `usable == true`. `usable` means files finalized with reconstructable accounting; it does **not** assert complete commissions or intrabar sampling. Also inspect `commissions_complete`, DST/data-quality flags, and coverage for the rule being evaluated. `Running`, `Failed`, missing, or unparsable metadata is incomplete. A write exception disables logging and prints one diagnostic without interrupting trading. If failure prevents metadata replacement, the prior Running document remains unusable.

Passive `OnMarketData` captures Last events when provided. No series is added; calculation mode, Tick Replay, fill resolution, risk settings, and order behavior are not changed. Ordinary historical bars do not supply Last ticks; `historical_last_tick_count == 0` explicitly reports missing intrabar ordering. A nonzero count still does not prove uninterrupted coverage or a faithful execution simulator. Market-data subscriptions can add overhead even when the logging flag is off.

Lucify evaluation/funded rules, account balances, resets, fees, payouts, and breach decisions belong in Python. Logs describe the original strategy path. If a simulated breach would flatten positions, suppress future orders, change size, or restart mid-position, replaying the remaining original trades is a counterfactual approximation. The simulator needs an explicit policy or fresh strategy runs for those cases. No exact intrabar breach result should be claimed from bar-only data.

## pandas loading

```python
import json
from pathlib import Path
import pandas as pd

run = Path(r'C:\path\to\run_id')
metadata = json.loads((run / 'run_metadata.json').read_text(encoding='utf-8'))
assert metadata['completion_status'] == 'Finalized' and metadata['usable']
executions = pd.read_csv(run / 'executions.csv', dtype='string', keep_default_na=False)
for column in ['execution_quantity', 'execution_price', 'commission', 'realized_pnl']:
    executions[column] = pd.to_numeric(executions[column].replace('', pd.NA))
# Reject/resolve TimezoneUnresolved observations before interpreting timestamps as instants.
unresolved = executions.data_quality.str.contains('TimezoneUnresolved')
executions['instant'] = pd.to_datetime(executions.timestamp.where(~unresolved), utc=True)
```

## Validation

Run `powershell -File Strategies/MyStarterPlaybook/tests/run.ps1` from the project root. It compiles the dependency-free logger with the Windows .NET Framework compiler, exercises accounting/IO fixtures under a German numeric locale, validates CSV/JSON, and checks original trading-body hashes. Install pandas in the Python environment to additionally check pandas ingestion. Harness artifacts are ignored by Git.

The runner optionally accepts `-NinjaTraderBin 'C:/Program Files/NinjaTrader 8/bin' -NinjaTraderCustomAssembly '<your NT user data>/bin/Custom/NinjaTrader.Custom.dll'` to compile the adapter against installed assemblies without deploying anything. The duplicate-enum warning from referencing an already installed strategy is suppressed only for that reference compilation.

Validation performed here: the ledger compiled with .NET Framework; fixtures and pandas ingestion passed, including partial entries, multi-lot partial exits, reversal accounting, orderless snapshots, platform/fixed/unknown commissions, duplicate/missing IDs, simultaneous events, DST ambiguity, concurrent run isolation, and metadata IO failure. Source hashes preserve original trading bodies and default settings. Both implementation sources compiled against the installed NinjaTrader Core, Gui, and Custom assemblies.

Required platform acceptance: compile both source files in NinjaTrader 8, then compare the original baseline, logging disabled, and logging enabled on identical Analyzer data/parameters/session/fill/commission settings. Compare order actions and timestamps, executions, prices, quantities, inventory, trade totals, and final strategy performance. Run both layering settings, stops/targets, session-close/orderless fills, and replay partial fills where available. Check an overnight exchange session and DST dates against NinjaTrader's trading-day display. Verify output path failures disable only logging. Actual NinjaTrader callback timing, runtime property availability, and Analyzer equivalence cannot be certified by the standalone harness or reference compilation.
