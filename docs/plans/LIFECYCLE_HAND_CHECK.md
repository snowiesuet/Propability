# Hand-calculated evaluation-to-payout example

Status: illustrative fixture for reviewing the study model; not a provider-rule guarantee. Prepared November 2, 2026.

This fixture checks the intended arithmetic for one evaluation and its funded account. It uses no historical strategy observations and does not establish expected performance.

## Explicit assumptions

- One $25K FLEX evaluation, then one $25K funded account with a fresh $25,000 balance, as approved for this study. This is a modeling choice, not an agreement confirmation.
- One MNQ round trip per listed day. Gross trade P&L is reduced by the modeled $1 round-trip commission ($0.50 per side) before applying account rules.
- DLL checks use completed-trade net session P&L and lock at a $600 loss. None of the example sessions approaches the DLL.
- Evaluation consistency uses the conservative strict 50% model. The example passes under both strict 50% and the published cushion because its largest day is well below either threshold.
- For the payout, use the table's interpretation of 50% of current payout-cycle net profit, capped at $1,000. Request approval/receipt is immediate by user policy; payout processing, settlement, and post-request trading pauses are ignored. On request, lock the MLL at $25,100, deduct the gross request, credit 90% immediately, then breach if the remaining account balance reaches or falls below the locked floor.
- No payout processing fee or other external cost is included. Unknown fees are excluded, not established as zero.

## Evaluation

Start at $25,000. Each of five sessions has one trade with $301 gross P&L and $1 commission, for $300 net per session.

| Check | Calculation | Result |
| --- | --- | ---: |
| Total evaluation profit | 5 × $300 net | $1,500 |
| Ending evaluation balance | $25,000 + $1,500 | $26,500 |
| Profit target | $1,500 ≥ $1,250 | Passes |
| Largest winning day | $300 / $1,500 | 20%; passes strict 50% |
| Purchase cost | One new evaluation | $43.20 |

The funded account starts separately at $25,000 under the fixture assumption; evaluation profits do not transfer.

## First funded payout

Four sessions each produce $101 gross less $1 commission = $100 net. The fifth session produces $851 gross less $1 commission = $850 net. The account is flat after the fifth trade.

| Check | Calculation | Result |
| --- | --- | ---: |
| Qualifying days | Five separate days at ≥$100 net | 5; eligible |
| Cycle profit | 4 × $100 + $850 | $1,250 |
| Balance before request | $25,000 + $1,250 | $26,250 |
| Maximum gross request | min(50% × $1,250, $1,000) | $625 |
| Minimum request | $625 ≥ $500 | Satisfied |
| Same-session profit check | $625 request ≤ $850 fifth-session net profit | Satisfied under the on-demand model |
| Trader receipt | 90% × $625 | $562.50, immediate by user policy |
| Firm share | 10% × $625 | $62.50 |
| Account after gross deduction | $26,250 − $625 | $25,625 |
| Locked loss floor | Request locks floor at $25,100 | $525 balance above floor |

Before unknown external fees, one modeled receipt less the one evaluation purchase is $562.50 − $43.20 = **$519.30**. Trading commissions have already been deducted from account P&L and are not subtracted a second time. This is a fixture total, not the 50-purchase study's net-cash result.

## Open decisions this fixture does not settle

- The payout page's prose and table conflict on whether the cap uses balance or profit. This fixture follows the user-selected table/current-cycle-profit interpretation.
- The user-selected payout/floor ordering is a model policy, not a confirmed provider sequencing rule.
- Payout-processing or payment-method fees and any other external costs.
- The account's subsequent DLL/floor behavior, later payout cycles, household slot waiting, and discretionary live review.

## Source references

- [LucidFlex payout rules](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts)
- [LucidFlex drawdown rules](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown)
- [LucidFlex consistency rules](https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage)
- [LucidFlex DLL/on-demand customization](https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization)
- [MNQ commission schedule](https://support.lucidtrading.com/en/articles/11508978-approved-products-and-commissions)
