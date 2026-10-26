# Account Engine — Implementation Plan

Status: increments 1–3 implemented and tested (October 26, 2026). Historical integration and the 50-account study remain later milestones.

## Incremental delivery checkpoints

1. **Complete — accounting foundation.** `AccountLedger` and immutable `CompletedTrade` inputs in `Strategies/MyStarterPlaybook/simulator/account_engine.py`. Decimal accounting, commissions deducted once, net trade statistics, session P&L totals, closed-trade drawdown, audit events, independent activation, and input ordering checks. Nine new tests and all 13 legacy replay tests pass. Trading-body integrity checks also pass.
2. **Complete — loss limits.** Explicit immutable `AccountRules`, `AccountEngine`, and `SessionClose`; fixed-floor breach checks, net-session DLL equality/skip behavior, terminal protection, and observed session closure/reset. Twelve additional hand-calculated tests pass, for 21 account tests plus all 13 legacy replay tests. Run `demo_loss_limits.py` under the simulator directory for visible synthetic examples.
3. **Complete — session-end rules.** Explicit EOD trailing distance/cap, evaluation target/strict consistency, funded qualifying days, and idempotent data-end sealing. Twelve additional tests cover EOD-only/final-balance ratcheting, nondecreasing/capped floors, equality breaches, delayed/equality passing, loss-day consistency, empty/losing/qualifying days, terminal protection, and unclosed final sessions. All 33 account tests plus 13 legacy replay tests pass. Run `demo_session_rules.py` for visible synthetic examples.
4. **Next — validated historical adapter.** Prove flat-to-flat input, derive observed session closes, and reconcile both account types on the saved baseline, including skipped trades and unchanged legacy replay behavior.

The standalone ledger includes every supplied trade. The engine supports explicit fixed/EOD trailing policies, net-session DLL, evaluation passing, and funded qualifying-day counts. EOD policy is `max(old_floor, min(cap, highest_completed_balance - trailing_distance))`; evaluation consistency is strict `best_winning_day <= consistency_limit * total_net_profit`. These are development-model policies, not resolution of outstanding provider nuances. The research draft remains non-executable. No study CLI, payout eligibility, or historical account-engine result is available yet. `finish_data()` leaves active accounts unfinished, preserves terminal outcomes, and never fabricates a final session close.

## Goal and boundaries

Build a small Python engine that answers: given completed trades and session boundaries, does one evaluation pass, breach, or remain unfinished, and does one funded account survive?

Use Python 3.10+, the standard library, and Decimal money arithmetic. No intrabar replay, synthetic exits, 50-account orchestration, purchases, withdrawals, bank settlements, dashboard, or randomized trials in this step. Those later systems will consume the engine's results.

Keep the existing `validate` and observation-based `replay` commands and their results unchanged. Add the completed-trade engine alongside them rather than forcing the old replay to adopt different loss-check semantics.

## 1. Inputs and public interface

Add `account_engine.py` under the existing simulator directory, with immutable input/rule dataclasses and one mutable account object:

- `AccountRules`: account type, starting capital, drawdown distance/cap, optional DLL, optional evaluation target/consistency, qualifying-day profit threshold, and an explicitly selected consistency policy. Evaluation requires a target and consistency; funded rejects evaluation pass criteria.
- `CompletedTrade`: stable trade ID, entry/exit timestamps, session ID, source ordering key, quantity, gross P&L, and commission. Net P&L is derived once as gross minus commission. Use individual P&L increments, never cumulative source balances.
- `SessionClose`: session ID and source timestamp/order establishing completion. This is separate from the trade stream, so no-trade sessions can close without inventing trades.
- `AccountEngine(account_id, rules)` with `apply_trade(trade)`, `close_session(event)`, `snapshot()`, and `finish_data()`. Each mutating method returns its new audit events; snapshots contain JSON-serializable account statistics with money represented as decimal strings.

Reject duplicate IDs, nonfinite values, negative commissions, unsupported quantity/inventory, out-of-order input, and trades assigned to an already closed session. Preserve chronological source order when timestamps tie. Each account owns its own state; the same source trade can be applied independently to multiple accounts.

## 2. State and rule processing

Track balance, net/gross P&L, commissions, current session P&L, highest completed-session balance, loss floor, best winning day, completed/qualifying days, trade wins/losses/breakevens, and maximum closed-trade balance drawdown.

Statuses are `active`, `passed`, or `breached`; DLL lockout is a separate per-session flag. Data exhaustion leaves active accounts unfinished rather than declaring a breach.

For each completed trade:

1. If the account is terminal, return an ignored-trade event without changing financial state. If DLL-locked, return a skipped-trade event with the same protection.
2. Add gross P&L and deduct commission once; update session P&L, trade statistics, and closed-trade drawdown.
3. Check balance against the loss floor; equality breaches. A hard breach takes precedence over a simultaneous DLL touch.
4. Otherwise, if session net P&L is at or below minus the configured DLL, lock that account through session end. Future trades in that session are excluded; do not fabricate liquidation.

At observed session completion:

1. Finalize that session's net P&L, best winning day, and qualifying-day count. For the selected funded fixture, a day qualifies at net P&L >= $100.
2. Ratchet the floor from the highest completed-session balance, capped by the configured locked floor, without ever decreasing it. Log old/new floor and triggering balance. Check hard breach after the update.
3. For evaluations only, check target and consistency while terminal-safe. With positive total profit, consistency is best winning day divided by total net profit. Excess consistency delays passing; it does not breach.
4. Clear the DLL lock and initialize the next session only when new-session input arrives. Duplicate closure is rejected. Never count an unobserved final close.

Funded accounts never pass an evaluation target. Track qualifying days as raw eligibility inputs only; do not claim payout eligibility until the later payout engine applies all payout rules. No payout-cycle reset is needed before withdrawals are implemented.

## 3. Adapter and explicit development scenario

Add a completed-trade adapter using the existing validated run and session-day function. Keep input validation and Analyzer reconciliation intact. The current supported baseline is one-contract, no-layering, flat-to-flat trades; reject partial/layered/reversal cases instead of treating arbitrary trade segments as complete positions.

- Build net trade increments from validated gross results and $0.50 per contract per side ($1 per one-MNQ round trip). Do not also subtract logged net costs.
- Derive observed session-close events from existing timestamp/session transitions in the validated data. Price marks are not loss-check inputs for this engine. Do not require tick data or force-close the last session.
- Use an explicit development rule fixture: $25,000 start, $1,000 EOD trailing distance, $25,100 cap, $600 session DLL, $1,250 evaluation target, strict 50% consistency, and $100 funded qualifying-day threshold. Funded has no target or consistency condition.
- Label strict 50%, net daily accounting, and the precise floor formula as development-model policies. They do not resolve the provider's unpublished cushion, trail-threshold nuances, or DLL above-trail mechanics. Keep the full research draft non-executable; do not silently turn unknown provider fields into defaults.
- Permit rule variation through explicit constructor/config inputs. Reject unsupported consistency modes or missing required engine values. Payout timing, live review, funded-slot handling, and the user's study start date do not block this independent engine.

No new public CLI is required in this step. Exercise real-data ingestion through an integration test/helper; publish a study command only when the coordinator is implemented.

## 4. Tests and acceptance

Keep the existing 13 tests passing. Add `test_account_engine.py` with hand-calculated fixtures covering:

- Net P&L and commissions deducted once; fresh activation ignores all prior source P&L.
- Loss-floor equality, EOD-only ratcheting, never lowering, cap behavior, and hard-breach priority.
- DLL equality, skipped later trades, next-session recovery, and independent account lockouts.
- Evaluation target plus strict consistency at completed session end, delayed passing, losses reducing consistency denominator, and no pass check on an unclosed final session.
- Funded survival without target/consistency, $100 day equality, losing/no-trade days, and unfinished data-end status.
- Duplicate/out-of-order input rejection, stable same-timestamp order, session rollover/DST labeling, and terminal account state immutability.
- Two accounts receiving identical inputs independently, and a later-start account matching the same rebased standalone suffix.
- Trade wins/losses/breakevens, average win/loss, and observed drawdown reconciled to fixture totals. Empty ratios return N/A.

Run the adapter and both account types against the validated historical baseline and reconcile balance to included trades minus commissions, accounting for DLL skips. Do not assert equivalence between the new closed-trade result and the legacy mark-to-market result; instead prove the unchanged legacy replay retains its previous outcome.

**Done when:** account fixtures and baseline integration reconcile, existing replay tests still pass, and the reusable engine exposes deterministic account events/snapshots for the next lifecycle phase. Update README/roadmaps with actual evidence; do not claim the 50-account or payout study is complete.

## Next phase

Use the tested engine to coordinate up to 50 paid evaluations and their funded descendants. Add payout/cash accounting and the [goal scorecard](SIM_PROP_PLAN.md#primary-goal-and-scorecard) after their policies are specified.
