# Phase 2 comparison review

Reviewed: October 25, 2026. Scope: logging OFF versus ON, layering disabled as reported by the user.

## Result

PASS for the supplied Analyzer trade and summary exports. Both trade files are byte-for-byte identical; all 547 rows and 23 named columns match in order, with zero field differences.

Compared fields include instrument, account, strategy, direction, quantity, entry/exit prices and timestamps, signal names, profit, cumulative profit, commissions/fees, MAE, MFE, ETD, and bars in trade.

| Metric | Logging OFF | Logging ON |
| --- | --- | --- |
| Trades | 547 | 547 |
| Total P&L | -$2,432.50 | -$2,432.50 |
| Maximum drawdown (Analyzer summary) | -$5,900.50 | -$5,900.50 |
| Commissions (Analyzer summary) | $0 | $0 |
| First trade entry | January 2, 2026 09:55:00 | January 2, 2026 09:55:00 |
| Last trade exit | October 23, 2026 12:25:00 | October 23, 2026 12:25:00 |

## Evidence

- OFF trades: `logging-off/analyzer-trades.csv`.
- ON trades: `logging-on/analyzer-trades.csv`.
- Both trade files SHA-256: `F9CB2AA89C23EFD82EDF27962E2C41C1069E65CF88DD003A4A632D0AAB566583`.
- Summaries: `logging-off/analyzer-summary.csv` and `logging-on/analyzer-summary.csv`.
- Both summary files SHA-256: `F074755F71D4E3B93A4785D5A776A6EB3DA56042E5E4F50D2C4913564146AF16`.
- Logging-OFF screenshot confirms logging disabled and layering disabled.

## Remaining limits and work

This verifies equality of the supplied Analyzer exports. It does not independently prove all runtime settings, order lifecycle events, or logger accounting match Analyzer.

- Layering-enabled comparison remains pending.
- Logging-ON settings and the new matching logger run folder still need to be saved/verified.
- `logging-on/0.1/` is an older run ending October 21, with 542 closed segments and -$2,182.50 gross realized P&L. Preserve it as an older baseline; it cannot reconcile the newer 547-trade run.
- Commissions are zero in Analyzer; this is not a cost-adjusted profitability result.
- Original pre-instrumentation comparison and remaining platform edge cases remain pending.

The previously supplied daily Analysis export has been replaced by the correct individual Trades export. Individual-trade ON/OFF comparison with layering disabled is complete. An initial Python prototype can proceed using explicitly identified input runs and limitations; full Phase 2 acceptance remains open.

## Subsequent input validation — October 25

After user folder reorganization, `logging-on/0.1/` now holds run `20261025T1948510645143Z_da023b58acb14391a3d93cbeb2cf8a67`, with 547 segments and -$2,432.50 gross P&L, plus the matching Analyzer exports. The earlier 542-segment data is no longer present at that path. The Python validator reconciles the current run's execution inventory, every trade, summary totals, daily gross totals, and sampled equity. See `../simulation-results/v0.1/20261025T202249Z_3fbf4a08/report.md` for results and hashed provenance. Historical ON/OFF comparison above records the previously inspected exports; the current logging-OFF archive contains a daily Analysis export again, so do not use that archive as a fresh individual-trade comparison without restoring its Trades export. Layering/full platform acceptance remain pending.
