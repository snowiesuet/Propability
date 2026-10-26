# Sim Prop Simulator — 50-Attempt Cash-Profit Plan

Status: revised plan; implementation pending. Updated: October 26, 2026.

This replaces the earlier first-release plan that deferred payouts and fees. The simulator must model evaluation and funded rules, withdrawals, and all applicable costs before reporting cash profitability.

## Primary goal and scorecard

Answer: **Does this strategy turn 50 paid prop evaluations into funded accounts and payout income after costs?** The main deliverable is a compact Stat / Value table like the user's example, backed by per-account results. The example's numbers, batches of 10/15 accounts, and probability estimates are illustrative only; they do not change the agreed sequential 50-purchase protocol or selected FLEX rules.

| Stat | Definition |
| --- | --- |
| Backtest | Source date range, observed trading sessions, and completed source trades |
| Trade win rate | Positive net source trades / all completed source trades; report losses and breakevens separately |
| Average win / loss | Mean positive net trade and mean negative net trade, in dollars |
| Realized reward/risk | Average winning trade / absolute average losing trade; not a configured target ratio |
| Evaluations purchased | Actual count against the target of 50 |
| Evaluation pass rate | Passed evaluations / purchased evaluations, shown as count and percent |
| Evaluation breach rate | Breached evaluations / purchased evaluations, shown as count and percent |
| Evaluations pending | Undecided evaluations and data-shortfall count; never silently count as failures |
| Resolved evaluation pass rate | Passed / (passed + breached), separately labeled so the denominator is explicit |
| Funded accounts | Passed evaluations versus accounts actually activated; active, breached, and waiting counts |
| Accounts receiving a payout | Funded accounts with at least one modeled bank receipt / funded accounts activated |
| Payout count / dollars | Settled payout count and total net trader receipts; requested/approved/unsettled amounts separate |
| Evaluation fees / other costs | Actual purchase count times $43.20 plus separately recorded external cash costs |
| Net cash profit | Modeled bank receipts minus external cash costs; $2,160 purchase fees only if all 50 are purchased |
| Time to pass / first payout | Median and range among accounts reaching each outcome; show sample counts |

Compute strategy-level trade statistics once from the validated source results at the selected study sizing/cost basis; never multiply source trade counts by the number of copied accounts. Report any account-filtered trade statistics separately. Empty denominators or absent winners/losers produce N/A, not invented zeros or infinite ratios.

The key economic finding is whether total modeled receipts exceed costs, alongside pass/breach and payout counts. A profitable historical study is evidence about this replay, not proof of future profitability. A single sequential study cannot produce the example's repeated-cycle probabilities or expected values; those require separately specified repeated trials and are deferred.

## Current status and next step

**Latest priority:** implement the independent account engine now, following [ACCOUNT_ENGINE_PLAN.md](ACCOUNT_ENGINE_PLAN.md). Its explicit development policies permit component implementation and tests while the full study's remaining payout/lifecycle specification is resolved in parallel. This does not authorize guessing provider rules or claim the full research draft is executable.

**Phase 1 is partially complete; lifecycle implementation has not started.** The existing executable remains the DLL-off/40% single-evaluation prototype. The selected DLL-on/50% study configuration is a research draft, not accepted by that loader.

Completed: FLEX screenshots saved, PRO archived separately, $43.20 purchase price and $600 DLL ON confirmed, official-rule research saved, and draft JSON syntax/settings checked. Fifty purchases would cost $2,160 before other costs. No 50-attempt study has run.

**Next deliverable: an execution specification that closes or explicitly classifies every draft configuration gap.** Work in this order:

1. Resolve the remaining mechanics needed for completed-trade replay: DLL session reset and above-trail behavior; floor lock ordering; consistency cushion/rounding; qualifying-day/cycle accounting; funded starting capital; payment fees and settlement behavior. Save evidence alongside dated research. Intraday enforcement and liquidation mechanics are deferred, not prerequisites for this version.
2. Obtain user choices for historical start date and withdrawal timing/amount. Document the suggested policy for review before adopting it: request the maximum permitted amount while flat after five completed qualifying days, at the next permitted request time. This is a proposal, not a confirmed policy.
3. Resolve what happens when a passed evaluation has no funded slot, and how to handle discretionary live review. Enforce the five-funded/ten-total limits. Any hypothetical transition or waiting policy must be labeled; do not silently continue unsupported trading.
4. Use the user-approved completed-trade model below. No intrabar data collection or liquidation reconstruction is required for this release.
5. Produce a validated execution configuration and hand-calculated evaluation/funded/payout fixture. Start Phase 2 once its rule inputs are settled. Independent account-state and ledger infrastructure can be developed meanwhile, but must reject unresolved rules rather than fill them with defaults.

Acceptance for this step: every required value has evidence or a named approved modeling policy; missing values produce clear validation errors; no historical result is presented as authoritative while required mechanics/data remain unresolved.

## Completed-trade model — approved simplification

The user approved ignoring intrabar data for now. Consume completed trade results in chronological order, deduct trading costs once, and update each account's realized balance. Check DLL and maximum-loss limits after each completed trade; trail the loss floor only at session end. Apply daily consistency, qualifying-day, payout, and purchase-fee rules to those results.

If the closed-trade DLL threshold is reached, lock that account for the rest of the session and exclude subsequent trades from its results; resume the next session. If a closed-trade maximum-loss check breaches, stop that account. Do not fabricate an early exit, intrabar fill, or open-position liquidation.

Report this as a completed-trade simulation: limits touched while trades were open are not captured. This limitation is a disclosure, not an implementation blocker. Keep the existing observation-based single-evaluation prototype unchanged and separately labeled.

## Simulation protocol

- Run 50 purchased evaluation attempts sequentially on one historical timeline. A failed evaluation counts as one attempt. A passed evaluation and its resulting funded account belong to the same attempt.
- Evaluation purchase price: $43.20 USD per attempt, explicitly confirmed by the user on October 26, 2026, replacing $65. Fifty purchases cost $2,160 before other costs. Hold this selected scenario price fixed and charge only actual purchases; this is not a claim that the coupon remains available for future purchases. The displayed $50 reset fee is not charged under the current new-purchase protocol.
- Begin at a selected eligible flat session start. After an evaluation passes or fails, start the next evaluation next eligible trading session, until 50 evaluations have been purchased.
- Maintain at most one active evaluation. Funded accounts continue independently alongside later evaluations, using the same subsequent historical strategy trades and separate rule/accounting state.
- Respect the researched household limit of five active funded accounts and ten combined evaluation/funded accounts. Block a sixth funded activation; passed-evaluation waiting/expiry and resulting purchase scheduling require an explicit policy before execution.
- After evaluation 50 starts, continue all active accounts until their supported terminal conditions or historical data exhaustion. Do not create evaluation 51, rewind data, fabricate trades, or treat an unfinished account as a failure.
- If available data cannot support 50 purchases, report the actual count and the shortfall. Do not claim 50 completed cycles while funded accounts remain active.
- Preserve Python 3.10+, standard-library CLI/report delivery, existing validation/replay commands, original exports, and NinjaTrader trading behavior. Start with one MNQ contract per account.

## Rule fidelity and cash accounting

- Use the corrected [FLEX evaluation and funded screenshots](../../rules/user_supplied_25k_flex_2026-10-26.md): $1,250 evaluation target, $1,000 EOD evaluation drawdown, 50% selected evaluation consistency, no funded consistency, five $100 profit days, funded scaling, and free activation. DLL is ON at $600, explicitly confirmed by the user; its enforcement basis, lockout mechanics, and any applicability changes after the initial trail still require definition. Keep the earlier PRO screenshot as an archived reference only; do not combine its 40% funded consistency, $250 payout target, or three-day payout condition with FLEX.
- Require a dated rule configuration and matching checkout fee schedule. User-supplied rules are accepted scenario inputs. The existing LucidFlex $25K snapshot remains a separate reference; do not silently import its funded payout, consistency, or scaling rules into this scenario.
- Explicitly configure evaluation targets, consistency, minimum/qualifying winning days where applicable, position limits, drawdown, DLL behavior, session boundaries, trading cutoffs, funded activation, payout cycles, withdrawals, and terminal policies.
- Trail each account's loss floor explicitly according to its configured firm rules. Distinguish EOD floor updates from intraday enforcement; never substitute intraday peak trailing for an EOD rule. Log the prior/new floor, reference balance, cap/lock, timestamp, and reason for each update.
- Keep consistency violations, soft daily lockouts, delayed payout eligibility, and account-ending breaches distinct. Apply rules only to stages where they belong.
- Track payout eligibility, request, approval, account deduction, and bank receipt as separate events. Apply the firm's profit split, processing fees, and withdrawal effect on the loss floor in the confirmed order.
- Headline net cash profit equals bank receipts minus evaluation purchases, paid resets, and other external cash costs. Funded balances, evaluation gains, eligible/requested/approved but unpaid payouts do not count as bank receipts.
- Deduct commissions and account-level trading fees once from account P&L. Do not deduct them again as external cash expenses unless separately paid from the trader's bank account. Report gross payout requests and net receipts separately.
- In a backtest, bank receipts are modeled settlements under an explicit confirmed timing policy, not evidence of real deposits. Real paper-trading cash reports require receipt evidence.
- Unknown prices, payout timing, or rule mechanics remain unresolved. Missing required inputs block an authoritative run rather than defaulting to zero or an invented rule.
- The 50-attempt study has no monthly purchase-budget constraint, retaining the user's earlier choice; every purchase still incurs its configured fee. Reset purchases are disabled for this protocol: a failed evaluation ends the attempt and its replacement is a new paid evaluation. Supporting a paid reset policy later requires explicit attempt-counting and fee rules.

## Phase 1 — Confirm protocol, rules, and data

- October 26 research is saved in [official-rule findings](../../rules/lucidflex_25k_research_2026-10-26.md) and a [draft study configuration](../../rules/lucidflex_25k_dll_on_50pct_study_draft.json). Confirmed values are captured; Phase 1 remains open for the listed execution gaps. This draft is not loadable by the existing provisional replay command.
- Preserve the existing dated reference and create a separate versioned execution configuration with source links, effective dates, fees, and confirmed policies.
- Resolve checkout variant, actual purchase prices, activation charges, other fees, drawdown enforcement/lock boundaries, consistency calculation, qualifying-day definitions, payout policy/timing, and funded/live terminal behavior.
- Specify a deterministic withdrawal policy: request timing and amount must be chosen before simulation, not adjusted after seeing results.
- Validate fills, P&L, commissions, inventory, timestamps, and session boundaries against Analyzer exports.
- Use validated completed-trade results and closed-trade loss checks. Intrabar/tick data and liquidation reconstruction are deferred by user choice; retain a brief model limitation in reports.

**Done when:** the run's required rule, fee, payout, and data inputs are explicit and reviewable, with no invented provider requirements or execution assumptions.

## Phase 2 — Account engine and auditable drawdown

- Separate validated historical events, rule configuration, and per-account state; parse input once.
- Support independent evaluation/funded engines with rebased P&L, costs, session history, drawdown floor, consistency, winning days, scaling limits, and breach/lockout state.
- Preserve current provisional replay behavior as a separate supported mode; do not silently relabel it as the strict simulator.
- Record every floor update and terminal/eligibility decision with its triggering observation and rule.

**Done when:** hand-calculated fixtures verify floor ratchets/caps, equality boundaries, costs, stage-specific rules, consistency/winning days, and stop/lockout behavior.

## Phase 3 — Fifty-attempt lifecycle, payouts, and cash ledger

- Add a study CLI accepting start date, an attempt count defaulting to 50, and the confirmed execution configuration.
- Schedule evaluations and funded activation according to the selected protocol and confirmed activation rules; never reuse a terminating trade or inherit evaluation profits into funded capital unless explicitly required by the firm.
- Maintain stable attempt/account IDs and evaluation-to-funded relationships. A failed account does not stop other accounts.
- Process payout eligibility, withdrawal requests, approvals, settlement, and funded balance/floor changes using the configured policy. Account termination does not automatically settle or cancel pending payouts; apply the confirmed policy.
- Charge every evaluation and applicable external fee to a dated cash ledger. Attribute shared costs once at study level rather than duplicating them per account.
- Preserve pending activations and unsettled payouts at data end. Do not invent live fills after a discretionary transition; report unsupported transitions separately.

**Done when:** a manually reconciled fixture demonstrates failures, passes, concurrent funded accounts, payouts, fees, data exhaustion, and the 50-purchase cap with correct net cash totals.

## Phase 4 — Reports, historical acceptance, and documentation

- Export attempt/account summaries, account traces, drawdown updates, payout events, cash ledger, validation, provenance, and a readable study report into a new output directory.
- Report attempts purchased versus 50 requested, passed/failed/unresolved evaluations, funded breaches/survivors, completed cycles, durations, sampled drawdown, receipts, costs, net cash profit, and pending payments.
- Reconcile cash totals to ledger entries, payout deductions to account balances, and summary counts to individual attempts. Keep unresolved/uncertain outcomes separate.
- Hash inputs, source-backed rules, fees, resolved policies, and all simulator code affecting results.
- Retain existing tests; add lifecycle, drawdown, consistency/winning-day, payout split/timing, withdrawal-floor, cost double-counting, same-timestamp ordering, session/DST, account-isolation, insufficient-data, and 50-attempt-limit tests.
- Compare the first provisional evaluation with existing replay and independently replay funded activation periods. Repeat identical studies to verify reproducible outcomes.
- Run the complete study on validated historical data once Phase 1 requirements are satisfied. If observations are insufficient, deliver a clearly qualified study instead of claiming strict compliance.
- Document commands, outputs, supported rules, unresolved limitations, and acceptance evidence; keep the project roadmaps synchronized with actual implementation and acceptance status.

**Done when:** reported outcomes and cash profit reconcile to source observations and configured rules, and any shortfall, pending settlement, unsupported transition, or intrabar uncertainty is explicit.

## Inputs still required before an authoritative study

1. Selected scenario is FLEX $25K, DLL ON at $600, $43.20 per evaluation, 50% evaluation consistency, no funded consistency, and free activation. Confirm applicable rule dates, DLL enforcement mechanics, and any additional fees.
2. Resolve drawdown/session enforcement and consistency or winning-day details applicable to the chosen configuration.
3. Confirm funded activation, withdrawal amount/timing policy, approval/settlement mechanics, and treatment of pending payouts after termination.
4. Choose the historical start date and use available validated completed-trade history; report fewer purchases if history ends before attempt 50. Intrabar data is not required.
5. Define treatment of live review or other provider terminal events without assuming a guaranteed transition date.

## References

- [Existing simulator](../../Strategies/MyStarterPlaybook/simulator/README.md)
- [Project overview](../../Strategies/MyStarterPlaybook/docs/project.md)
- [Detailed roadmap](../../Strategies/MyStarterPlaybook/docs/roadmap-detailed.md)
- [Dated LucidFlex reference and unresolved inputs](../../rules/lucidflex_25k_2026-10-22.md)
- [Selected FLEX evaluation and funded rules](../../rules/user_supplied_25k_flex_2026-10-26.md)
- [October 26 official-rule research](../../rules/lucidflex_25k_research_2026-10-26.md)
- [Draft 50-attempt study configuration](../../rules/lucidflex_25k_dll_on_50pct_study_draft.json)
- [Archived PRO screenshot reference](../../rules/user_supplied_25k_funded_2026-10-26.md)
