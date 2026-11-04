# Lifecycle policy choices for review

Status: user-selected modeling policies; not official provider rules. Updated November 3, 2026.

User-selected policies are already captured in [SIM_PROP_PLAN.md](SIM_PROP_PLAN.md): start January 1, 2026; request the maximum payout at the first eligible time flat; model approval and receipt immediately; ignore payout processing, settlement, and post-request trading pauses. Five qualifying days remain required.

The following choices affect simulated outcomes. User selections are recorded below; unknown provider details remain visible as limitations rather than being treated as settled terms.

| Open item | Recommended study policy | What it changes |
| --- | --- | --- |
| Funded starting balance | **User approved:** start each $25K funded account fresh at $25,000; do not carry evaluation profit forward. | Defines funded profit, drawdown, and payout calculations; remains a study assumption, not an agreement confirmation. |
| Payout cap profit basis | **User approved:** use 50% of net profit in the current payout cycle, capped at $1,000, with a $500 minimum. | Sets each request amount. The provider page conflicts between “account balance” prose and “profit” table; the table and current-cycle net are the study interpretation. |
| Account deduction / floor order | **User approved:** lock the MLL at $25,100 on request, deduct the gross request, pay 90% immediately, and breach if the remaining balance reaches or falls below the locked floor. | The exact sequencing is a study policy; the official drawdown page says reaching the MLL breaches and the floor locks on payout request. |
| Unlisted external fees | Do not invent fees or treat unknown fees as zero. Show net cash after known purchase costs as “before unverified external fees.” | Keeps the cash result qualified until fee evidence is available; no choice needed unless you have fee data. |
| Account capacity limits | **User approved:** ignore the five-funded/ten-total account limits; do not queue or delay activations for capacity. | Study will not claim compliance with those provider limits. |
| Live promotion trigger | **User selected:** model promotion when an account receives payout 5. The provider says payout 5 enters risk review; a move is discretionary, not guaranteed. | A deterministic study assumption to model the requested path. On an actual trader-wide move, Lucid says all eligible funded accounts with at least one payout move live and remaining sim accounts close. The lifecycle coordinator must represent that closure behavior. |
| Live account stage | Model the $25K live account at $0 with $1,000 EOD drawdown, no DLL, and a 20-micro maximum. Track the EOD floor and first live bonus eligibility/receipt using the published $2,000 profit, 20 qualifying days, $1,000 gross bonus, and 90/10 split. | Supported published mechanics; live fills remain the historical strategy's completed trades. |
| Ordinary live payouts | **Unmodeled:** the source says daily payouts but does not state request sizing/caps or payout sequencing. | Do not include ordinary live withdrawals in cash receipts until a source or approved policy supplies these details. |
| Further live bonuses | Track the first objective cycle only. Do not assume how a repeatable monthly cycle resets beyond the published target and 20-day objectives. | Prevents inventing recurrence timing or reset behavior. |
| Cashout on live offer | Follow the selected live path; do not take the alternative cashout. | The source describes a 24-hour response window and automatic live move if no cashout choice is made. The model uses an immediate live transition at payout 5 as a simplification. |

### Boundary example

Suppose the account has $25,600 and requests $500. Lock the floor at $25,100, then deduct $500; the remaining $25,100 balance touches the floor, so the account is breached. This uses the official equality-breach rule with the user's selected $25,100 floor.

The one-account hand calculation in [LIFECYCLE_HAND_CHECK.md](LIFECYCLE_HAND_CHECK.md) uses the selected assumptions for illustration. These choices make the lifecycle runner's behavior reviewable; they do not make them official provider terms. The runner should retain the unresolved/assumed labels in its output and should not claim an authoritative provider-rule result.

## Source basis

- [LucidFlex payouts](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts)
- [LucidFlex drawdown](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown)
- [Lucid maximum account limits](https://support.lucidtrading.com/en/articles/11404617-maximum-number-of-accounts)
- [Lucid new live structure](https://support.lucidtrading.com/en/articles/16558826-new-live-structure)
- [Lucid live trading times](https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times)
