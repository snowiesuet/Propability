# Payout-5 and LucidLive hand check

Status: synthetic fixture for lifecycle acceptance; not historical strategy performance or a guarantee of provider promotion. Prepared November 3, 2026.

## Funded payout 1

Start a fresh funded account at $25,000. Net closed-trade results are $100 on four sessions, then $850 on a fifth session. Each of the five days meets the study's $100 net qualifying-day threshold.

| Check | Calculation | Result |
| --- | --- | ---: |
| Current-cycle profit | 4 × $100 + $850 | $1,250 |
| Balance before payout | $25,000 + $1,250 | $26,250 |
| Gross request | min(50% × $1,250, $1,000) | $625 |
| Minimum / same-session limit | $625 ≥ $500 and ≤ $850 | Eligible |
| Trader receipt | 90% × $625 | $562.50 |
| Firm share | 10% × $625 | $62.50 |
| Balance after gross deduction | $26,250 − $625 | $25,625 |
| MLL after request | Locked floor | $25,100 |
| Remaining headroom | $25,625 − $25,100 | $525; account survives |

This matches [LIFECYCLE_HAND_CHECK.md](LIFECYCLE_HAND_CHECK.md). The payout cap basis and immediate receipt remain selected study policies; processing and payment fees are unknown.

## Live transition and first bonus

The lifecycle coordinator treats an account's fifth approved payout as the trigger for the selected trader-wide move. Other active funded accounts with at least one payout move live too; remaining simulated accounts close. Lucid's live page describes payout 5 as entry to discretionary review, while its payout page summarizes five payouts as the live transition. The study selects the deterministic transition policy.

For each eligible $25K account moved live:

| Check | Calculation | Result |
| --- | --- | ---: |
| Live starting balance | Published rule | $0 |
| Initial drawdown | Published rule | $1,000 |
| Locked floor | After $1,000 generated live profit | −$100 |
| Bonus profit target | Published rule | $2,000 |
| Qualifying days | 20 days, each with at least one trade and session net ≥$1 or ≤−$1 | 20 |
| Bonus | Published gross amount | $1,000 |
| Trader receipt | 90% × $1,000 | $900 |

The synthetic integration fixture feeds a deterministic repeated pattern for enough sessions to reach payout 5, transition eligible accounts, continue live trading, complete the first bonus objective, and reconcile cash receipts minus known fees. It is intentionally synthetic because the available historical stream did not reach a payout.

## Remaining limits

- Actual live promotion is discretionary; this study triggers it at payout 5 by policy.
- Ordinary live payout sizing/caps are not stated in the linked structure page and remain unmodeled.
- The source calls the bonus repeatable/monthly but does not specify the next cycle's reset mechanics; only the first objective/receipt is modeled.
- The synthetic path verifies lifecycle arithmetic and transitions, not trading performance or live fill behavior.

## Source references

- [LucidFlex payouts](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts)
- [New Live Structure](https://support.lucidtrading.com/en/articles/16558826-new-live-structure)
