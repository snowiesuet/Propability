# Strategy versions and backtest runs

The first FairPriceStrategy iteration is **v0.1**. Strategy versions and backtest runs are separate: changing a date range or rerunning Analyzer does not create a new strategy iteration.

- Preserve a source snapshot and manifest under `versions/v0.1/`.
- Existing v0.1 data stays at its current paths, indexed by `versions/v0.1/manifest.json`. After the user folder reorganization, `logs/logging-on/0.1/` contains the current 547-trade run. The earlier 542-trade run is retained as a historical manifest record without an available data path.
- For future exports, use `logs/v0.1/<run_id>/` with `logger/`, `analyzer-on/`, and `analyzer-off/` subfolders as applicable. Use the logger metadata run ID to identify the run.
- Never overwrite previous runs. Different parameters, date ranges, costs, or layering settings need separate run folders and recorded settings.
- When trading logic changes for the next iteration, create `v0.2`, preserve its source snapshot, and keep its runs separate.
- A logging-only change should record its source revision/schema without implying a new trading strategy iteration.
- Keep original metadata and CSV exports unchanged. Record version labels, assumptions, and validation findings in manifests/reports.
- Store future simulator results separately under `simulation-results/<strategy_version>/<simulation_id>/`, referencing the source run ID, rule snapshot, configuration, and simulator revision.

The v0.1 source snapshot records the current workspace source. It is not proof of the precise source used by an older run unless that run recorded matching hashes.
