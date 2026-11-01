# Cohort simulation debug and validation

Validation checks: **passed**. Source run `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.
Trades consumed: 547 / 547.
Accounts: 10; passed 2, breached 7, unfinished 1.

## Account by account

| Attempt | Source trades | Trades used | Result | Ending balance | Net P&L |
|---:|---:|---:|---|---:|---:|
| evaluation-01 | 1–42 | 42 | breached | $24208.00 | $-792.00 |
| evaluation-02 | 43–63 | 21 | breached | $24004.00 | $-996.00 |
| evaluation-03 | 64–107 | 44 | breached | $23956.00 | $-1044.00 |
| evaluation-04 | 108–124 | 17 | breached | $23983.00 | $-1017.00 |
| evaluation-05 | 125–187 | 63 | breached | $24812.00 | $-188.00 |
| evaluation-06 | 188–242 | 55 | breached | $24145.00 | $-855.00 |
| evaluation-07 | 243–318 | 76 | breached | $24198.50 | $-801.50 |
| evaluation-08 | 319–386 | 68 | passed | $26307.00 | $1307.00 |
| evaluation-09 | 387–477 | 91 | passed | $26302.00 | $1302.00 |
| evaluation-10 | 478–547 | 70 | unfinished | $25105.00 | $105.00 |

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
