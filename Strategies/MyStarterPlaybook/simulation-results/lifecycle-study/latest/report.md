# 50-purchase lifecycle study

| Stat | Value |
|---|---|
| Backtest | 195 days, 547 trades (2026-01-02–2026-10-23) |
| Win rate | 38.0% (208 / 547) |
| Win / loss | +$128.41 / -$87.58 |
| RR | 1.47 |
| Evaluations purchased | 10 / 50 |
| Eval pass rate | 2 / 10 (20.0%) |
| Eval breach rate | 7 / 10 (70.0%) |
| Eval unfinished / closed | 1 |
| Funded accounts | 2 activated; 0 moved live |
| Funded per 15 evaluations | 3.0 observed ratio |
| Funded payouts | 0 gross $0.00; receipts $0.00 |
| At least 1 payout | 0 / 2 |
| Payout 5 / live | 0 reached payout 5; 0 live accounts |
| Payout milestones | ≥2 payouts: 0; ≥3: 0 |
| Live bonus receipts | $0.00 |
| Ordinary live payouts | Unmodeled; payout amount/cap not stated in source |
| Evaluation fees | $432.00 net of modeled refunds |
| Net cash profit | -$432.00 before unverified external fees |
| Evaluation time to pass | mean 28.0; range 23–33 trading sessions; n=2 |
| Evaluation time to breach | mean 16.1; range 6–27 trading sessions; n=7 |
| Funded time to first payout | N/A (n=0) |
| Funded time in stage | mean 42.5; range 26–59 trading sessions; n=2 |

## Account-by-account results

Each attempt joins its evaluation, funded, and live stages. Session ranges and durations use observed trading sessions.

| Attempt | Eval | Eval period | Eval P&L | Eval trades (CONT/REV; per day) | Eval WR / RR | Funded | Funded trades (CONT/REV; per day) | Payouts | Live | Live trades (CONT/REV; per day) | Live WR / RR |
|---:|---|---|---:|---|---|---|---|---:|---|---|---|
| 1 | breached | 2026-01-02–2026-01-21 (14 sessions) | $-792.00 | 42 (6/36; 3.00/day over 14 days) | 33.3% / 1.30 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 2 | breached | 2026-01-22–2026-02-03 (9 sessions) | $-996.00 | 21 (2/19; 2.33/day over 9 days) | 14.3% / 1.63 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 3 | breached | 2026-02-04–2026-02-23 (14 sessions) | $-842.00 | 42 (3/39; 3.00/day over 14 days) | 31.0% / 1.52 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 4 | breached | 2026-02-24–2026-03-03 (6 sessions) | $-1017.00 | 17 (4/13; 2.83/day over 6 days) | 17.6% / 1.05 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 5 | breached | 2026-03-04–2026-04-01 (21 sessions) | $-135.00 | 60 (5/55; 2.86/day over 21 days) | 41.7% / 1.34 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 6 | breached | 2026-04-02–2026-05-01 (22 sessions) | $-855.00 | 55 (7/48; 2.50/day over 22 days) | 30.9% / 1.55 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 7 | breached | 2026-05-04–2026-06-11 (27 sessions) | $-801.50 | 76 (7/69; 2.81/day over 27 days) | 38.2% / 1.33 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 8 | passed | 2026-06-12–2026-07-14 (23 sessions) | $1307.00 | 68 (5/63; 2.96/day over 23 days) | 48.5% / 1.47 | unfinished | 158 (18/140; 2.68/day over 59 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 9 | passed | 2026-07-15–2026-09-03 (33 sessions) | $1403.00 | 90 (8/82; 2.73/day over 33 days) | 47.8% / 1.45 | unfinished | 68 (10/58; 2.62/day over 26 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |
| 10 | unfinished | 2026-09-04–2026-10-23 (26 sessions) | $-193.00 | 68 (10/58; 2.62/day over 26 days) | 36.8% / 1.62 | not_funded | 0 (0/0; 0.00/day over 0 days) | 0 ($0) | not_started | 0 (0/0; 0.00/day over 0 days) | N/A / N/A |

## Model notes

- DLL above the initial trail is unresolved; modeled as $600 throughout funded stage.
- Evaluation consistency uses strict 50%; published cushion is omitted, which may reduce passes.
- Qualifying-day basis is modeled using completed-trade net daily P&L >= $100.
- Payout amount/floor sequence and immediate settlement are user-selected study assumptions.
- Unknown payout/payment and external costs are not established as zero; net is before unverified fees.
- Payout 5 promotion is modeled as immediate/trader-wide although actual risk-team transition is discretionary.
- Ordinary live payouts and bonus cycles after the first are unmodeled.
- Completed-trade model excludes intratrade loss-limit touches; final unobserved session is not force-closed.
- This is one chronological historical replay; no repeated-cycle probability estimates are implied.

CONT/REV count entry signal prefixes. Per-day averages divide stage trades by all observed trading sessions in that stage, including no-trade sessions. `account-lifecycle.csv` also gives sessions with trades and separately counts other signal prefixes. Detailed stage metrics and event traces are in `account-lifecycle.csv` and `lifecycle-study.json`; source-level daily counts and P&L are in `session-summary.csv`.
