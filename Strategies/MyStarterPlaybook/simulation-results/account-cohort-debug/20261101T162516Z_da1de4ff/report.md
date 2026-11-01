# Cohort simulation debug and validation

Validation checks: **passed**. Source run `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.
Selected period: 2026-04-01 through 2026-06-30 (inclusive session dates).
Trades consumed: 176 / 176 selected trades (full source: 547).
Accounts: 3; passed 0, breached 2, unfinished 1.

## Account by account

| Attempt | Source trades | Trades used | Result | Ending balance | Net P&L |
|---:|---:|---:|---|---:|---:|
| evaluation-01 | 1–54 | 54 | breached | $23996.00 | $-1004.00 |
| evaluation-02 | 55–133 | 79 | breached | $24145.50 | $-854.50 |
| evaluation-03 | 134–176 | 43 | unfinished | $25357.00 | $357.00 |

## Inspecting the trace

Open `events.csv` and sort by `event_index` (already in source order). Each row records the account, source event, trade P&L, engine event names, balance, session P&L, floor, DLL lock, and status before and after processing.

## Checks performed

- Original inputs pass the existing historical validator and adapter reconciliation.
- Every consumed trade receives exactly one engine disposition.
- No source trade ID is consumed twice.
- Each account balance equals starting capital plus applied gross P&L less applied commissions.
- Account trade and DLL skip counters match the emitted dispositions.
- Outcome totals sum to the number of accounts started.

This checks implementation consistency and makes each decision inspectable; it does not prove that the provisional rule assumptions match provider rules. Funded continuation and payouts are outside this sequential debug run.
