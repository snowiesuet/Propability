# LucidFlex $25K — official-rule research

Checked: October 26, 2026 (America/New_York). This dated research supplements the user's FLEX screenshots and preserves the October 22 reference unchanged. It is not a complete account agreement or an executable rulebook.

Selected study: 50 sequential purchases, $43.20 each, DLL ON ($600 from the screenshot), 50% evaluation consistency, one MNQ per account, free funded activation, no resets. Price is a user-selected fixed study input, not a promise of future coupon availability. PRO remains separate.

## Findings by source

### Drawdown

Evaluation and funded accounts trail at session close. For $25K, the loss allowance is $1,000, the published trail threshold is $26,100, and the locked floor is $25,100. A payout request moves the floor to the locked value. Touching the loss floor breaches. The initial $24,000 floor is derived from nominal capital less the allowance. [Official drawdown article](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown)

The article does not settle intraday realized versus unrealized enforcement, commission basis, exact equality at the trail-lock threshold, or ordering of withdrawal deductions and floor locking. EOD floor updates must not be confused with EOD-only breach checks.

### DLL and on-demand requests

An enabled DLL applies to both stages. Reaching it locks trading until the next session rather than ending the account. DLL-on enables intraday payout requests between 18:00 and 15:45 ET; requesting one pauses funded trading through the rest of the trading day. Hedging violations remove intraday eligibility. [Official customization article](https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization)

The $600 amount comes from the user's screenshots. Reviewed Flex pages do not fully define net/gross or unrealized loss basis, liquidation price/cost, exact reset mechanics, or the funded screenshot's below-initial-trail qualification. Do not import PRO's LucidScale formula.

### Evaluation consistency

The calculation divides the largest profitable day by total account profit. An excessive ratio delays passing rather than breaching. The selected limit is 50%. A published $25K example allows a $650 largest day at $1,250 profit through a percentage-dependent cushion. [Official consistency article](https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage)

The general cushion formula and rounding are absent. Do not encode a universal $25 cushion or infer a general 52% limit. Strict 50% is a possible named conservative scenario, not an exact reproduction of the provider's cushioned eligibility.

### Payouts

Eligibility requires five separate days earning at least $100 and positive cycle profit. Approval resets the qualifying-day requirement. Requests range from $500 to half of account profit, capped at $1,000. The trader receives 90%. There is no separate payout buffer. Requests are final; deteriorating balance before processing may cause denial. Approval is followed by account deduction within minutes and payment-method disbursement within two business days. [Official payouts article](https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts)

The prose says account balance while its table says profit; use the table as the documented interpretation and retain this conflict. Net/gross day basis, cycle reset ordering, approval delay, pending-payment treatment after breach, bank arrival, and processing fees remain unresolved. Disbursement to a payment method is not confirmed bank receipt.

### Funded sizing

Evaluation has no scaling tiers. Funded $25K begins at 1 mini or 10 micros and rises to 2 minis or 20 micros at $1,000 profit. Tiers update at session end and may fall after losses or withdrawals. One MNQ remains below these positive-profit tiers. [Official scaling article](https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan)

Below-zero-profit tier treatment is not explicit in the displayed table.

### Account limits and lifecycle constraint

A household may hold at most five funded accounts and ten total evaluation/funded accounts. Evaluation accounts can remain in reserve. [Official account limits](https://support.lucidtrading.com/en/articles/11404617-maximum-number-of-accounts)

This corrects the earlier unlimited-funded assumption. A sixth funded activation must be blocked. How a passed evaluation waits, expires, or affects the next purchase is not specified by this article and remains a lifecycle policy/input to resolve.

### Live transition

Five payouts is a ceiling, not a guaranteed minimum before live review. Earlier discretionary transitions are possible. Live transition closes remaining simulated accounts; eligible funded accounts have received at least one payout. [Official new live structure](https://support.lucidtrading.com/en/articles/16558826-new-live-structure)

A backtest cannot infer the risk team's decision from historical trades alone. Stop with an unsupported-transition status or use an explicitly hypothetical policy; do not fabricate continuing simulated payouts or live executions.

### Sessions, trading costs, and activation

The hours article requires closing by 16:45 EST, permits reopening at 18:00 EST, and requires earlier holiday closes. Automatic cutoff liquidation is not itself an account-ending violation. The fixed EST wording versus seasonal Eastern time needs clarification. [Official hours](https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times)

MNQ commission is $0.50 per contract per side. Additional external costs have not been established as zero. [Official commission table](https://support.lucidtrading.com/en/articles/11508978-approved-products-and-commissions)

The evaluation article confirms the $1,250 target and free activation and describes a 5–30 minute funded upgrade. Next-session activation remains the user's simulation policy, not a provider requirement. Its summary's no-DLL description conflicts with its optional-DLL benefit and the customization page; use the user's selected DLL-on configuration. [Official evaluation article](https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account)

## Execution gaps and next work

**Subsequent user decision:** intrabar data is deferred. The active study uses completed-trade net results, loss checks after each closed trade, and session-end floor updates. Intrabar/liquidation reconstruction is not a prerequisite. Item 6 below describes the stricter model's data limitation, not a blocker for the approved completed-trade study. Official ambiguities remain documented separately from this chosen simulation model.

1. Obtain provider clarification for DLL accounting/liquidation, funded above-trail behavior, intraday MLL enforcement, lock-boundary rounding, and 50% consistency cushion.
2. Resolve net-of-fees qualifying days, payout processing/order, fees, and actual bank settlement assumptions.
3. Choose withdrawal timing/amount before replay; on-demand availability does not require immediate withdrawal.
4. Resolve funded-slot waiting and discretionary live-transition policy. Strict mode must not exceed five funded accounts.
5. Select the start date and session/holiday calendar. Confirm fresh funded capital and actual reset mechanics from the applicable agreement.
6. Address data limitations: current historical bar-close/fill observations lack tick coverage. DLL liquidation can change later inventory and P&L, so simply skipping trades after a DLL touch cannot establish an exact replay. Require executable liquidation observations or explicitly qualify the approximation.

The accompanying JSON is a research draft, not compatible with the existing single-evaluation loader. Unknown mechanics stay null; strict execution must reject unresolved inputs. No simulator behavior or historical source data was changed by this research.

## Change record versus October 22

- **User-selected scenario:** four proposed checkout variants become one selected DLL-on/50% study; unknown purchase price becomes $43.20, with the screenshot's $50 reset retained but unused.
- **DLL amount:** unknown becomes $600 from screenshots; the official customization source confirms soft lockout, while enforcement mechanics remain open.
- **Scope:** fees and payouts move into the first release; the study targets 50 actual purchases rather than independent start-date batches.
- **Concurrency:** the earlier study plan's unbounded funded accumulation is replaced by the official five-funded/ten-total limits.
- **Previously known mechanics:** drawdown cap, payout split/limits, consistency-cushion uncertainty, and live discretion are reaffirmed, not newly invented changes.
- Existing provisional replay results still use their recorded DLL-off/40% configuration. They are not results for this revised study.
