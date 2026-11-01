"""Run one completed-trade evaluation against a fully validated historical run."""

import argparse
import json
import sys
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from account_adapter import check_account, load_account_input
from account_engine import AccountRules
from replay import dump, load_config
from study_period import select_period


PROJECT = Path(__file__).resolve().parents[1]
SIMULATOR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=PROJECT / "logs/logging-on/0.1")
    parser.add_argument("--analyzer-trades", type=Path)
    parser.add_argument("--analyzer-summary", type=Path)
    parser.add_argument("--validation-config", type=Path, default=SIMULATOR / "configs/lucidflex_25k_provisional.json")
    parser.add_argument("--start-date", help="Inclusive session date, YYYY-MM-DD")
    parser.add_argument("--end-date", help="Inclusive session date, YYYY-MM-DD")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    args.analyzer_trades = args.analyzer_trades or args.run / "analyzer-trades.csv"
    args.analyzer_summary = args.analyzer_summary or args.run / "analyzer-summary.csv"
    config = load_config(args.validation_config.resolve())
    output = args.out or PROJECT / "simulation-results/account-engine" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    try:
        source = load_account_input(args.run, args.analyzer_trades, args.analyzer_summary,
                                    config, config["commission_per_contract_per_side"])
        selected_events, period = select_period(source.events, args.start_date, args.end_date)
        selected_source = replace(source, events=selected_events,
                                  observed_sessions=tuple(sorted({event.session_id for event in selected_events})),
                                  validation={**source.validation, "trade_count": period["trade_count"]})
        rules = AccountRules(
            starting_capital=Decimal("25000"), loss_floor=Decimal("24000"),
            daily_loss_limit=Decimal("600"), account_type="evaluation",
            loss_model="eod_trailing", trailing_distance=Decimal("1000"),
            floor_cap=Decimal("25100"), evaluation_target=Decimal("1250"),
            consistency_limit=Decimal("0.50"), consistency_policy="strict")
        result = check_account(selected_source, "historical-evaluation-1", rules)
        summary = {
            "status": "passed", "input_run_id": source.metadata["run_id"],
            "input_trade_count": source.validation["trade_count"],
            "observed_sessions": len(source.observed_sessions),
            "selected_period": period,
            "rules": {"starting_capital": "25000", "daily_loss_limit": "600",
                      "evaluation_target": "1250", "consistency_limit": "0.50",
                      "trailing_distance": "1000", "floor_cap": "25100",
                      "consistency_policy": "strict", "commission_per_contract_per_side": str(config["commission_per_contract_per_side"])},
            "validation": source.validation,
            "legacy_replay_result": source.legacy_result,
            "account": result,
            "input_hashes": list(source.input_hashes),
            "limitations": ["Completed-trade checks only; intratrade limit touches are excluded.",
                            "The final unobserved session is left open.",
                            "Strict 50% consistency and EOD trailing behavior are development assumptions."]}
        dump(output / "account-study.json", summary)
        snap = result["snapshot"]
        report = ["# Single historical evaluation replay", "",
                  f"Validated run: `{source.metadata['run_id']}`.",
                  f"Selected period: {period['start_date_inclusive'] or 'start'} through {period['end_date_inclusive'] or 'end'} (inclusive session dates).",
                  f"Selected input: {period['trade_count']} trades across {period['observed_session_count']} sessions; full source has {source.validation['trade_count']} trades.",
                  f"Outcome: **{snap['status']}**; data-end outcome: **{snap['outcome']}**.",
                  f"Balance: ${snap['balance']}; net P&L: ${snap['net_pnl']}; loss floor: ${snap['loss_floor']}.",
                  f"Applied trades: {result['reconciliation']['applied_trade_count']}; DLL skipped: {result['reconciliation']['dll_skipped_trade_count']}; terminal ignored: {result['reconciliation']['terminal_ignored_trade_count']}.",
                  f"Full source net after assumed commissions: ${source.validation['net_pnl_under_fixed_cost_assumption_full_run']} (validation total, not account outcome).", "",
                  "This is one historical replay, not a pass-rate estimate. Checks use completed trades; intratrade limit touches are excluded. The last session is not force-closed.",
                  "Details and source hashes are in `account-study.json`."]
        (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print(json.dumps({"status": "passed", "outcome": snap["status"],
            "data_end_outcome": snap["outcome"], "output": str(output.resolve())}))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        dump(output / "account-study.json", {"status": "failed", "error": str(exc)})
        print(f"Historical account replay failed: {exc}\nReport: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
