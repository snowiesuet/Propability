# Objective

Modify my existing NinjaTrader 8 NinjaScript strategy, **Cont & Rev**, to add comprehensive logging for a future Python-based prop firm backtesting simulator.

The simulator will model Lucify prop firm evaluations and funded accounts. I will provide Lucify's rules separately.

The purpose of this modification is to capture sufficient historical trading information to simulate:

* Repeated evaluation attempts.
* Evaluation pass/fail outcomes.
* Funded-account progression.
* Daily loss limits.
* Trailing and static drawdown rules.
* Payout eligibility.
* Account breaches.
* Evaluation and funded-account fees.
* Net profitability across repeated attempts.

**Important: Do not modify the existing trading strategy's entry logic, exit logic, risk settings, indicators, or order execution behavior. This task is for instrumentation only.**

## 1. Inspect the Existing Strategy First

Before making changes:

1. Read the entire existing NinjaScript strategy.
2. Identify the strategy's entry and exit logic.
3. Identify how orders, executions, positions, realized P&L, and unrealized P&L are currently handled.
4. Identify the calculation mode, trading session configuration, instrument, and timeframe.
5. Determine whether the strategy uses managed or unmanaged order handling.
6. Identify partial fills, multiple entries, scaling, stop-losses, profit targets, and other relevant order behaviors.
7. Identify any existing logging functionality.
8. Explain which events can be logged reliably and which require additional instrumentation.

Do not assume that one entry corresponds to one execution or that one execution corresponds to a complete trade.

Preserve the existing strategy behavior.

## 2. Create Machine-Readable CSV Logs

Create a dedicated output directory for the strategy's backtest logs.

The logs must be suitable for ingestion by Python using pandas.

Use invariant numeric formatting, ISO 8601 timestamps, explicit column headers, and consistent handling of missing values.

Avoid relying on human-readable Output window messages as the primary data source.

Prefer structured CSV files, with configurable logging enabled or disabled.

Create the following files.

### A. executions.csv

Record every actual order execution, including partial fills.

Required fields:

* run_id
* strategy_name
* instrument
* account_name, if available
* execution_id
* order_id
* order_name
* timestamp
* trading_day
* market_position
* execution_side
* execution_quantity
* execution_price
* commission
* realized_pnl
* position_quantity_after_execution
* average_position_price_after_execution

Requirements:

* Use actual execution information rather than assuming an order was filled at its requested price.
* Record partial fills individually.
* Preserve enough identifiers to associate executions with orders and positions.
* Do not double-count realized P&L.
* Document whether the P&L fields are gross or net of commissions.
* Clearly distinguish unavailable values from genuine zero values.

### B. trades.csv

Record completed trades or position lifecycle segments.

Required fields:

* run_id
* trade_id
* instrument
* direction
* entry_timestamp
* exit_timestamp
* entry_price
* exit_price
* quantity
* gross_realized_pnl
* commissions
* net_realized_pnl
* maximum_favorable_excursion, if available
* maximum_adverse_excursion, if available
* exit_reason
* entry_signal
* trading_day

Requirements:

* Correctly handle partial exits and multiple executions.
* Support reversals and multiple entries if the existing strategy permits them.
* Define clearly whether a trade means an individual entry-to-exit segment or an entire position lifecycle.
* Do not invent exit reasons when they cannot be determined.
* Ensure that the sum of trade-level net P&L reconciles with the strategy's realized P&L, subject to documented accounting differences.

### C. account_equity.csv

This file is particularly important for prop firm simulation.

Capture account state throughout the backtest at a sufficiently granular frequency to reconstruct drawdown and loss-limit breaches.

Required fields:

* run_id
* timestamp
* trading_day
* instrument
* account_balance
* cumulative_realized_pnl
* unrealized_pnl
* account_equity
* current_position_quantity
* average_position_price
* current_market_price
* session_realized_pnl
* session_unrealized_pnl
* session_start_balance

Requirements:

1. Log the account state at every completed bar at minimum.
2. Where necessary, add intrabar logging or another reliable mechanism to capture equity extremes.
3. If the strategy uses Calculate.OnEachTick or Calculate.OnPriceChange, avoid unnecessarily changing its existing calculation mode.
4. If the strategy uses Calculate.OnBarClose, do not claim that bar-close logs capture every intrabar drawdown breach.
5. Record intrabar equity highs and lows when feasible.
6. Record session transitions and daily resets explicitly.
7. Distinguish realized equity from mark-to-market equity.
8. Document whether the equity calculation includes commissions and other trading costs.
9. Preserve the strategy's existing session template and trading-hours configuration.

A completed-bar snapshot alone is insufficient to prove that a prop firm account would have survived an intrabar drawdown limit.

If the existing calculation mode cannot provide sufficient information, explain the limitation and recommend the least invasive way to capture the missing data without changing trading behavior.

### D. orders.csv

Record order lifecycle events.

Required fields:

* run_id
* timestamp
* order_id
* order_name
* order_type
* action
* order_state
* requested_quantity
* filled_quantity
* average_fill_price
* limit_price
* stop_price
* time_in_force
* rejection_reason

Include order submission, acceptance, changes, fills, cancellations, and rejections where applicable.

Use the appropriate NinjaTrader order and execution callbacks.

Avoid duplicate records when an order transitions through multiple states.

### E. sessions.csv

Record daily trading summaries.

Required fields:

* run_id
* trading_day
* session_start_timestamp
* session_end_timestamp
* starting_balance
* ending_balance
* starting_equity
* ending_equity
* gross_realized_pnl
* commissions
* net_realized_pnl
* maximum_intraday_equity
* minimum_intraday_equity
* maximum_drawdown_from_intraday_peak
* maximum_loss_from_session_start
* number_of_trades
* winning_trades
* losing_trades

Requirements:

* Define the trading-day boundary according to the configured trading-hours template.
* Handle sessions that cross midnight.
* Calculate intraday extrema from sufficiently granular observations.
* Document the exact drawdown calculation used.
* Do not substitute bar-close extrema for true intrabar extrema without explicitly identifying the limitation.

## 3. Add Run Metadata

Create a run_metadata.json file for each backtest run.

Include:

* run_id
* strategy_name
* strategy_version
* NinjaTrader version, if available
* instrument
* bar type
* bar interval
* backtest start date
* backtest end date
* trading-hours template
* time zone
* calculation mode
* commission configuration
* slippage configuration
* starting strategy capital
* strategy parameters
* relevant strategy settings
* logging version

Record the settings actually used for the run whenever possible.

Do not invent unavailable metadata.

This metadata will allow Python to identify and compare different backtest runs.

## 4. Prop Firm Rules Must Remain Separate

Do not hardcode Lucify's rules into the trading strategy.

The NinjaScript should record trading behavior and account-state information.

Python will separately implement the configurable prop firm rules, including:

* Evaluation profit target.
* Maximum drawdown.
* Static or trailing drawdown.
* Intraday versus end-of-day drawdown calculations.
* Daily loss limits.
* Consistency requirements.
* Minimum trading days.
* Funded-account rules.
* Payout eligibility.
* Withdrawal restrictions.
* Evaluation fees.
* Reset and activation fees.
* Profit splits.

The same historical trade data should be reusable to simulate different rule configurations.

Do not assume that NinjaTrader's strategy account balance is equivalent to a prop firm's simulated account balance.

## 5. Logging Implementation Requirements

Use appropriate NinjaTrader 8 lifecycle methods and event callbacks.

Potentially relevant methods include:

* OnStateChange()
* OnBarUpdate()
* OnOrderUpdate()
* OnExecutionUpdate()

Use these according to their intended purposes and the existing strategy architecture.

Requirements:

* Initialize logging resources safely.
* Close and flush files appropriately.
* Avoid writing duplicate execution records.
* Avoid blocking the trading thread with unnecessarily expensive file operations.
* Prevent file corruption from multiple simultaneous writes.
* Use unique run identifiers.
* Make file locations configurable.
* Handle missing directories and file-access errors.
* Log errors without silently discarding important data.
* Avoid excessive logging when disabled.
* Ensure the code compiles under the installed NinjaTrader 8 version.

If logging requires a separate helper class, implement it cleanly and document its dependencies.

Do not introduce external dependencies unless necessary.

## 6. Reconciliation and Validation

Add a validation report for each backtest run.

Compare:

* Strategy Analyzer total realized P&L.
* Sum of execution-level realized P&L, where comparable.
* Sum of completed trade-level net P&L.
* Total commissions.
* Ending strategy equity.
* Daily P&L totals.
* Execution counts.
* Completed trade counts.

Document expected differences between the various accounting methods.

Flag discrepancies rather than silently adjusting the data.

Verify that:

* Partial fills are recorded correctly.
* Cancelled and rejected orders are not treated as fills.
* Commissions are not double-counted.
* Open positions at the end of the backtest are identified.
* Session boundaries are handled consistently.
* No future information is used to calculate earlier account states.

## 7. Deliverables

Provide:

1. The modified NinjaScript source code.
2. A summary of the changes.
3. A list of every logging field and its meaning.
4. Example CSV output using clearly identified sample data.
5. Instructions for running a historical backtest in NinjaTrader.
6. Instructions for locating and exporting the generated files.
7. A Python validation script that loads the CSVs and checks their schemas, timestamps, missing values, and P&L reconciliation.
8. A list of any remaining data limitations relevant to prop firm drawdown simulation.

## 8. Acceptance Criteria

The modification is complete only when:

* The strategy compiles.
* Existing entry and exit logic remains unchanged.
* A historical backtest generates the required files.
* Executions, completed trades, orders, and account snapshots can be associated consistently.
* P&L and commissions can be reconciled against Strategy Analyzer.
* Session boundaries are correctly represented.
* Any limitations affecting intrabar drawdown calculations are documented.
* The output is ready for a separate Python prop firm simulator.

Before finalizing, explain any requested logging behavior that cannot be implemented reliably under the existing strategy's calculation mode.

**Priority: data correctness first, strategy behavior preservation second, logging performance third.**
