# Lifecycle study scorecard template

The final report should lead with a compact **Stat / Value** table inspired by the user's reference. Populate values only from the validated source replay and modeled lifecycle. Use `N/A` where a denominator or supported rule is unavailable; label modeled assumptions and keep unresolved values visible.

## Primary historical run

| Stat | Value |
| --- | --- |
| Backtest | `{observed sessions} days, {source trades} trades ({start}–{end})` |
| Win rate | `{positive net trades} / {all source trades}; {percent}` |
| Win / loss | `+${average winning net trade} / -${absolute average losing net trade}` |
| RR | `{average win / absolute average loss}` |
| Evaluations purchased | `{count} / 50` |
| Evaluation pass rate | `{passed} / {purchased} ({percent})` |
| Evaluation breach rate | `{breached} / {purchased} ({percent})` |
| Evaluations pending at data end | `{unfinished count}` |
| Funded accounts activated | `{count}` |
| Funded outcomes | `{active or live} active, {breached} breached, {unfinished} unfinished` |
| Accounts with ≥1 payout | `{count} / {funded accounts}` |
| Payouts before live transition | `{count}; gross $X, trader receipts $Y` |
| Payout 5 / live transitions | `{accounts reaching payout 5}; {accounts modeled live}` |
| Live bonus | `{eligible count}; modeled receipts $X` |
| Ordinary live payouts | `Unmodeled unless payout terms are sourced` |
| Evaluation fees | `${known fee total}` |
| Other external fees | `${known total}; unknown fees listed as limitations` |
| Net cash profit | `${modeled receipts less known external costs; before unverified fees}` |
| Evaluation time to pass / breach | `mean and range in trading sessions, with separate sample counts` |
| Funded time to first payout | `mean and range in trading sessions, with sample count` |
| Funded time in stage | `mean observed duration until breach, live move, or data end; sample count` |
| Study duration | `{observed trading days and calendar span}` |

Do not report account balances or payout requests as receipts. Net cash profit uses only modeled trader receipts less external cash costs; account trading costs have already reduced account P&L and must not be charged twice.

## Repeated-cycle analysis (separate, optional)

The user's example also includes batch probabilities such as “at least 3 funded,” “all accounts blown,” and mean payouts per cycle. Those require a separately specified repeated-trial design; they are not estimates from one chronological 50-purchase replay. If implemented, report the batch size, number of trials, sampling method, confidence intervals, cycle definition, and all assumed restart/overlap rules beside the results. Never mix those estimates into the primary historical-run table.

## Presentation

- Use the two-column Stat / Value table as the first result, followed by a short assumptions/limitations block and links to detailed per-account ledgers.
- Prefer user-friendly rows over every implementation diagnostic; keep reconciliation counts and audit detail in supporting files.
- Keep payout-cycle receipts, live bonus receipts, known costs, and net cash profit distinct.
- Report unavailable or unsupported measures as `N/A` / `Unmodeled`, never as zero.
- Include each account's own observed trading-session duration and start/end session in the detailed account ledger. Mark data-end durations as unfinished/censored, not completed lifetimes.
