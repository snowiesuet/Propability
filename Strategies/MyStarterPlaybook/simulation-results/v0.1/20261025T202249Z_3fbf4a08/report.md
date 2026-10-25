# v0.1 validation and evaluation replay

Input run: `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`.

Validation: passed. 547 trades; 1094 executions.
Gross P&L: $-2432.50; Analyzer net P&L with zero costs: $-2432.50.
Full-run assumed commissions: $547.00; full-run net after assumed costs: $-2979.50.

Provisional one-attempt outcome: **breach** at 2026-01-21T10:16:00.0000000-05:00.
Observed equity at stop: $24265.50; loss floor: $24266.00.
Replay stops at the first sampled breach/pass; full-run P&L above is a separate validation statistic.

## Scenario assumptions

- Historical scenario from the October 22 rules snapshot, not verified current provider terms.
- DLL-off configuration; no DLL amount is guessed.
- Strict 40% largest winning-day net profit / total net profit; no consistency cushion.
- Session changes at 18:00 on the Eastern source wall clock. Holiday/calendar details remain unverified.
- Loss floor ratchets only after a completed session, capped at 25100; equity <= floor breaches at observed samples.
- Pass eligibility is evaluated at completed session end while flat, after updating the floor.
- Only session rollovers observed in the input establish a completed session. The last session is not forced closed.
- One original MNQ contract only; no layering, quantity scaling, synthetic liquidation, or overnight positions.
- Fixed costs replace unknown/platform costs using gross P&L, never subtract both.
- Evaluation purchase fee is unknown; net cash profitability is unavailable.

Intrabar survival cannot be certified. This is one historical attempt, not a pass-rate estimate or a prediction.
Input hashes, resolved configuration, daily net totals, and event details are in the accompanying JSON/CSV files.
