"""Quick sequential evaluation cohort across one validated historical trade stream."""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from account_adapter import load_account_input
from account_engine import AccountEngine, AccountRules, CompletedTrade
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
    parser.add_argument("--max-attempts", type=int, default=50)
    parser.add_argument("--start-date", help="Inclusive session date, YYYY-MM-DD")
    parser.add_argument("--end-date", help="Inclusive session date, YYYY-MM-DD")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    args.analyzer_trades = args.analyzer_trades or args.run / "analyzer-trades.csv"
    args.analyzer_summary = args.analyzer_summary or args.run / "analyzer-summary.csv"
    config = load_config(args.validation_config.resolve())
    output = args.out or PROJECT / "simulation-results/account-cohort" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    try:
        source = load_account_input(args.run, args.analyzer_trades, args.analyzer_summary,
                                    config, config["commission_per_contract_per_side"])
        selected_events, period = select_period(source.events, args.start_date, args.end_date)
        rules = AccountRules(
            starting_capital=Decimal("25000"), loss_floor=Decimal("24000"),
            daily_loss_limit=Decimal("600"), account_type="evaluation",
            loss_model="eod_trailing", trailing_distance=Decimal("1000"),
            floor_cap=Decimal("25100"), evaluation_target=Decimal("1250"),
            consistency_limit=Decimal("0.50"), consistency_policy="strict")

        accounts = []
        active = None
        active_trade_count = 0
        consumed_trades = 0
        for event_index, event in enumerate(selected_events):
            if active is None:
                if len(accounts) >= args.max_attempts:
                    break
                active = AccountEngine(f"evaluation-{len(accounts) + 1:02d}", rules)
                active_trade_count = 0
            if isinstance(event, CompletedTrade):
                active_trade_count += 1
                consumed_trades += 1
                emitted = active.apply_trade(event)
            else:
                emitted = active.close_session(event)
            terminal = next((item for item in emitted if item["type"] in
                             ("account_breached", "evaluation_passed")), None)
            if terminal:
                active.finish_data()
                accounts.append({"account_id": active.snapshot()["account_id"],
                                 "outcome": active.snapshot()["status"],
                                 "trades_consumed": active_trade_count,
                                 "ending_snapshot": active.snapshot(),
                                 "terminal_event": terminal,
                                 "terminal_event_index": event_index})
                active = None

        if active is not None:
            active.finish_data()
            accounts.append({"account_id": active.snapshot()["account_id"],
                             "outcome": "unfinished",
                             "trades_consumed": active_trade_count,
                             "ending_snapshot": active.snapshot(),
                             "terminal_event": None,
                             "terminal_event_index": None})
        counts = {key: sum(account["outcome"] == key for account in accounts)
                  for key in ("passed", "breached", "unfinished")}
        result = {
            "status": "passed", "input_run_id": source.metadata["run_id"],
            "source_trade_count": source.validation["trade_count"],
            "selected_period": period,
            "max_attempts": args.max_attempts,
            "accounts_started": len(accounts), "outcome_counts": counts,
            "source_trades_consumed": consumed_trades,
            "source_trades_remaining": period["trade_count"] - consumed_trades,
            "source_trades_outside_period": source.validation["trade_count"] - period["trade_count"],
            "account_start_policy": "A fresh evaluation starts at the next source event after the prior evaluation passes or breaches.",
            "rules": {"starting_capital": "25000", "daily_loss_limit": "600",
                      "evaluation_target": "1250", "consistency_limit": "0.50",
                      "trailing_distance": "1000", "floor_cap": "25100",
                      "consistency_policy": "strict",
                      "commission_per_contract_per_side": str(config["commission_per_contract_per_side"])},
            "accounts": accounts,
            "validation": source.validation,
            "legacy_replay_result": source.legacy_result,
            "input_hashes": list(source.input_hashes),
            "limitations": ["Evaluation-only sequential attempts; funded accounts do not continue alongside later evaluations.",
                            "No purchase fees, activation, withdrawals, payout rules, or account-slot limits are modeled.",
                            "Completed-trade checks exclude intratrade limit touches.",
                            "The final unobserved session is not force-closed.",
                            "Strict 50% consistency and EOD trailing behavior are development assumptions."]}
        dump(output / "account-cohort.json", result)
        report = ["# Sequential evaluation cohort quick test", "",
                  f"Validated run: `{source.metadata['run_id']}`.",
                  f"Selected period: {period['start_date_inclusive'] or 'start'} through {period['end_date_inclusive'] or 'end'} (inclusive session dates).",
                  f"Selected input: {period['trade_count']} trades across {period['observed_session_count']} sessions; full source: {source.validation['trade_count']} trades.",
                  f"Evaluations started: {len(accounts)} (limit {args.max_attempts}).",
                  f"Passed: **{counts['passed']}**; breached: **{counts['breached']}**; unfinished: **{counts['unfinished']}**.",
                  f"Selected-period trades consumed: {consumed_trades}; remaining: {period['trade_count'] - consumed_trades}.",
                  "A new evaluation starts on the next source event after the prior evaluation terminates.",
                  "Funded accounts do not continue alongside later evaluations, and fees/payouts are omitted.",
                  "This is a quick sequential count, not the full lifecycle study. Intratrade touches are excluded; the final session is not force-closed.",
                  "Per-account outcomes and validation details are in `account-cohort.json`."]
        (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print(json.dumps({"status": "passed", "accounts_started": len(accounts),
                          "passed": counts["passed"], "breached": counts["breached"],
                          "unfinished": counts["unfinished"], "output": str(output.resolve())}))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        dump(output / "account-cohort.json", {"status": "failed", "error": str(exc)})
        print(f"Historical cohort replay failed: {exc}\nReport: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
