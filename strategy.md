# Cont & Rev — Version 1

Strategy version: **1**. Reviewed: October 25, 2026. This describes the current implementation, not a proposed strategy change.

Source: [NYOpenFairPriceStrategy.cs](Strategies/MyStarterPlaybook/NYOpenFairPriceStrategy.cs). NinjaTrader class/display name: `NYOpenFairPriceStrategy`. Project shorthand: FairPriceStrategy.

## Core idea

Use the configured opening bar's open as a fixed **fair price** for the day. First trade continuation in the opening candle's direction; later trade reversals toward fair price. Entries use a new structure break **or** a displacement candle; both are not required.

The source recommends NQ one-minute bars but does not enforce an instrument or timeframe. The saved historical run uses **MNQ DEC26, one-minute bars**.

## Opening reference and trading windows

The strategy evaluates signals on completed bars (`Calculate.OnBarClose`) after its 20-bar warmup.

At the bar whose timestamp matches `OpenHour:OpenMinute` (default **09:30**), it:

- Sets fair price to that bar's `Open[0]`.
- Saves the bar's high, low, and close.
- Classifies the opening candle as bullish if close > open, bearish if close < open. A doji permits no continuation entry.
- Resets the entry counter, continuation flags, and remembered structure levels.

Default windows, expressed in **bar timestamps**:

| Time | Behavior |
| --- | --- |
| 09:30 | Establish opening reference; no entry |
| 09:31–09:44 | Opening continuation |
| 09:45–10:59 | Mean reversion |
| 11:00 onward | No new entries |

These clock comparisons use `Time[0]`; there is no explicit conversion to New York time in the trading logic. The saved run records an Eastern source timezone. Bar timestamp conventions matter: the implementation selects the bar **stamped 09:30**, which should be checked against the intended market-open candle in NinjaTrader. It does not independently locate the first trade at 09:30.

## Signal definitions

### New break of structure (BOS)

- **Bullish:** current close exceeds the highest high of the preceding **5 bars**, excluding the current bar.
- **Bearish:** current close falls below the lowest low of the preceding **5 bars**, excluding the current bar.
- A break is considered new only if its reference level differs from the last recorded level in that direction by more than half a tick, or no level has been recorded yet.

Structure levels are recorded as soon as a new break is detected, even if no entry follows. This prevents repeated entry signals from the same recorded level.

### Displacement candle

All of the following must hold:

- Candle range is positive.
- Absolute body is **strictly greater than 1.20 × the preceding candle's absolute body**.
- **Combined upper and lower wicks** occupy at most **20%** of the total range.

A bullish displacement closes above its open; a bearish displacement closes below its open. The implementation measures both wicks together, despite the source comment's reference to a small counter-wick.

## Phase 1: opening continuation

Within the continuation window:

- Bullish opening candle → buy on a new bullish BOS **or** bullish displacement.
- Bearish opening candle → sell short on a new bearish BOS **or** bearish displacement.

The position must be flat, continuation must remain valid, and the entry counter must be below the session maximum. Only **one continuation entry submission** is permitted per opening reset, even if that trade exits quickly.

During elapsed minutes **1–3**, before a continuation entry has been submitted:

- A bullish opening candle's continuation becomes invalid if a later bar's low falls **below** the opening low.
- A bearish opening candle's continuation becomes invalid if a later bar's high rises **above** the opening high.

Invalidation is checked before entry on that bar and lasts until the next opening reset. It does not disable later reversion entries. There is no requirement to wait all three confirmation bars before entering.

## Phase 2: mean reversion

Within the reversion window:

| Price relative to fair price | Direction | Entry trigger |
| --- | --- | --- |
| Above fair price | Short | New bearish BOS, or bearish displacement within the override distance |
| Below fair price | Long | New bullish BOS, or bullish displacement within the override distance |

The signal close must be at least **10 points** from fair price. Displacement alone is allowed only when that distance is at most **38 points**. A new BOS can qualify at any distance of 10 points or more. At exactly fair price, no reversion entry qualifies.

By default, the position must be flat. Multiple reversion submissions are possible after earlier trades exit, subject to the shared entry limit. Continuation and reversion may both occur on the same day.

## Stops, targets, and exits

Each entry submits **one contract**, with a signal-specific stop-loss and profit target configured before the managed market entry. Distances are selected using **ATR(14) on the current chart bars**, at the signal bar:

| ATR(14), in price points | Stop distance | Fixed target distance |
| --- | --- | --- |
| Invalid or ≤ 0 | `StopPoints` (default 25) | `TargetPoints` (default 37.5) |
| > 0 and < 7 | 16.5 points | 24.75 points |
| ≥ 7 and ≤ 20 | `StopPoints` (default 25) | `TargetPoints` (default 37.5) |
| > 20 | 50 points | 75 points |

Fixed targets give a nominal **1.5:1 reward/risk ratio** at default settings, before costs and fill effects. Distances are converted to instrument ticks. Points are price units, not dollars.

Continuation always uses the dynamic fixed target. Reversion supports two modes:

- **`FixedPoints` (default):** use the dynamic fixed target above. The target is not necessarily fair price and can extend beyond it.
- **`FairPrice`:** use the distance between the signal close and fair price as the target distance; skip entry if that distance is not positive. This is a tick-distance target rather than an absolute-price order pinned to fair price, so a different entry fill can shift the resulting target price.

There is no explicit trailing stop, breakeven adjustment, time-based trade exit, or scale-out logic. The 11:00 cutoff stops entries; it does **not** close an existing position. Session-close liquidation is enabled with `ExitOnSessionCloseSeconds = 30`, using the configured trading session.

## Position limits and order handling

- Managed NinjaTrader orders; entry signals are `CONT_LONG`, `CONT_SHORT`, `REV_LONG`, and `REV_SHORT`.
- Default maximum: **4 entry submissions per opening reset**, shared across both phases. The counter increments at submission, not on a confirmed fill or completed trade.
- `AllowLayering = false` by default. When enabled, reversion can submit while a position exists, including opposite-direction signals; inventory and reversals then depend on managed order handling. Continuation still requires flat.
- `EntriesPerDirection = 10`, with `EntryHandling.UniqueEntries`. Reversion submissions reuse their direction's signal name.
- No strategy-level daily dollar loss limit, profit lock, or prop firm drawdown/payout rule is implemented.

## Defaults and saved-run settings

The opening/signal defaults are: `OpenHour = 9`, `OpenMinute = 30`, `ContinuationMinutes = 15`, `ReversionMinutes = 90`, `ConfirmationBars = 3`, `StructureLookback = 5`, `DisplacementMultiplier = 1.20`, `MaxWickPercent = 20`, `MinDistanceFromFair = 10`, and `DisplacementOverrideDistance = 38`.

The saved [run metadata](Strategies/MyStarterPlaybook/logs/logging-on/0.1/run_metadata.json) uses these defaults, fixed-point reversion targets, four maximum submissions, and layering disabled. It records MNQ one-minute bars, `CME US Index Futures ETH`, standard historical fill resolution, zero configured slippage, commissions excluded in Analyzer, and unknown logger commissions. These are saved-run settings; they do not establish the settings currently selected in the NinjaTrader UI.

Debug visuals are enabled by default. CSV logging is disabled by default but enabled in that saved run. Logging records observations and executions; it does not define trading signals. See [LOGGING.md](Strategies/MyStarterPlaybook/LOGGING.md) for schemas and accounting limits.

## Implementation limits to retain when interpreting results

- Opening state resets on the matching clock bar, not on a general session-start event. There is no guard confirming a fresh opening reference for the current date if the matching bar is absent or skipped during warmup.
- Bar-close signals do not imply fills at the signal close. Actual fills depend on NinjaTrader's execution/fill settings.
- Historical bar-close data cannot establish the order of every intrabar stop, target, or prop firm drawdown event. The saved run has no historical Last-tick observations.
- This document describes behavior; it does not establish profitability or prop firm eligibility. Provider rules and the future simulator remain separate; see [project.md](Strategies/MyStarterPlaybook/project.md) and the dated [LucidFlex reference](rules/lucidflex_25k_2026-10-22.md).
