# v0.1 evaluation replay

Python 3.10+; standard library only. This prototype validates the first strategy iteration and replays one evaluation attempt from the beginning of a selected run. NinjaScript and original exports are left unchanged.

From the repository root:

```powershell
python Strategies/MyStarterPlaybook/simulator/replay.py replay `
  --run Strategies/MyStarterPlaybook/logs/logging-on/0.1 `
  --analyzer-trades Strategies/MyStarterPlaybook/logs/logging-on/0.1/analyzer-trades.csv `
  --analyzer-summary Strategies/MyStarterPlaybook/logs/logging-on/0.1/analyzer-summary.csv
```

Replace `replay` with `validate` to produce only validation/provenance reports. A failed check returns a nonzero exit code and prevents simulation. The terminal prints the output directory.

## Outputs and versions

Every invocation creates a new folder under `simulation-results/v0.1/<UTC timestamp>_<unique suffix>/`. Optional `--out <new-directory>` selects another destination; existing directories are rejected. Reports never overwrite input data or past results.

- `validation.json`: counts, gross P&L reconciliation, daily gross/net totals, and full-run assumed costs.
- `provenance.json`: input paths and SHA-256 hashes, source run ID, strategy version, simulator revision/code hash, rule snapshot hash, and resolved scenario settings.
- `result.json`: single-attempt outcome, observed balance/equity, floor, and stopping timestamp.
- `events.csv`: observed fills, completed sessions, floor updates, and terminal decision.
- `report.md`: readable findings and scenario assumptions.

Full-run validation P&L and the single-attempt stopping balance are different measures. The attempt stops at its first sampled breach or pass. Later strategy results do not revive a breached account.

## Validation scope

The validator checks finalized/usable metadata; expected schemas; run/instrument identities; event sequence and timestamp ordering; actual execution inventory, entry basis, and realized P&L; unique fill/trade associations; segment P&L; every Analyzer trade's direction, quantity, prices, times, names, and profit; summary totals; equity state at each observation; daily gross reconciliation; valid bars; counts; and observed range.

Supported input is MNQ at $2/point, historical unit fills, one position contract at most, no layering/reversal fills, no overnight holdings, and flat initial/final inventory. Analyzer timestamps must use the logger source wall clock, in the exported US date format, at second precision. The prototype currently reconciles zero-cost Analyzer reference exports only; it rejects cost-bearing exports rather than guessing fee semantics. It requires every fill to have a reliable unique ID and an associated execution equity observation. Unsupported data fails validation.

The fixed replay commission replaces logged costs using gross accounting: `$0.50 × filled contracts` per execution. It never subtracts both logged net costs and the scenario commission. The actual input's commission mode is Unknown; the assumed rate is not a measured result. Partial fills, layering, and other unsupported inventory cases must be added with validation before using those runs.

## Provisional rule scenario

Default configuration: [configs/lucidflex_25k_provisional.json](configs/lucidflex_25k_provisional.json). Use `--config` for an explicit alternative file within the supported model.

This is a historical scenario based on the dated October 22 reference, not a claim about current provider terms. It models $25,000 starting balance, $1,250 target, $1,000 EOD trailing loss allowance capped at a $25,100 floor, DLL off, and strict 40% consistency. One original MNQ contract is used without quantity multiplication.

Scenario choices that still require provider confirmation:

- Daily reset at 18:00 on the recorded Eastern wall clock; embedded offsets handle the input's DST. No independent provider holiday calendar is implemented. Exchange `trading_day` is validated as a date but is not substituted for the configured reset day.
- At the next observed session, the prior session's final flat balance updates the highest EOD balance and loss floor. The floor never decreases; equality breaches.
- Breach checks use net marked equity at every available equity observation, including fill observations, and stop immediately. Recorded marks are approximate Last/bar-close marks, not executable bid/ask liquidation quotes.
- Pass eligibility is checked at completed session end while flat: net profit meets target and largest winning session / total net profit is at most 40%. No consistency cushion is guessed.
- The last session is left unclosed if the next rollover is absent. Data exhaustion without pass/breach is `incomplete`, not failure.

No historical Last ticks were captured in the current run. An unobserved intrabar breach may have occurred before the reported stop. A sampled pass would not prove survival. No synthetic liquidation, exit cost, or broker balance is invented at breach; an open position at stop is reported as such.

Purchase fees are unknown, so net cash profitability is unavailable. DLL-on, funded stages, payouts, resets/repeated attempts, alternate start dates, position scaling, inactivity policies, and a complete provider rulebook are outside this first implementation.

## Tests

```powershell
python -m unittest discover -s Strategies/MyStarterPlaybook/simulator/tests -v
```

Boundary tests cover equality breaches, entry-side cost effects, EOD-only ratcheting, cap behavior, consistency, final-session censoring, stop-on-breach behavior, overnight rejection, offset/timestamp handling, invalid inputs, and single deduction of costs. The full real-run invocation above separately exercises reconciliation against Analyzer.
