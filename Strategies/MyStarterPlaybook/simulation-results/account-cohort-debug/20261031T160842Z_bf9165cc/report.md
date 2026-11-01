# Cohort simulation debug and validation

Validation checks: **passed**. Source run `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.
Trades consumed: 547 / 547.
Accounts: 10; passed 2, breached 7, unfinished 1.

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
