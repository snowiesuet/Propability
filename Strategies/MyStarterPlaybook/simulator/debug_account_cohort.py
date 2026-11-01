"""Replay the sequential evaluation cohort with a row-by-row audit trace."""

import argparse
import csv
import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from account_adapter import load_account_input
from account_engine import AccountEngine, AccountRules, CompletedTrade
from replay import dump, load_config, require
from study_period import select_period


PROJECT = Path(__file__).resolve().parents[1]
SIMULATOR = Path(__file__).resolve().parent
TRACE_FIELDS = [
    "event_index", "trade_index", "account_id", "source_event_type", "timestamp",
    "source_order", "session_id", "trade_id", "gross_pnl", "commission", "net_pnl",
    "decision_events", "balance_before", "balance_after", "session_net_before",
    "session_net_after", "loss_floor_before", "loss_floor_after", "dll_locked_before",
    "dll_locked_after", "status_before", "status_after", "outcome",
]


def _rules() -> AccountRules:
    return AccountRules(
        starting_capital=Decimal("25000"), loss_floor=Decimal("24000"),
        daily_loss_limit=Decimal("600"), account_type="evaluation",
        loss_model="eod_trailing", trailing_distance=Decimal("1000"),
        floor_cap=Decimal("25100"), evaluation_target=Decimal("1250"),
        consistency_limit=Decimal("0.50"), consistency_policy="strict")


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
    output = args.out or PROJECT / "simulation-results/account-cohort-debug" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    try:
        source = load_account_input(args.run, args.analyzer_trades, args.analyzer_summary,
                                    config, config["commission_per_contract_per_side"])
        selected_events, period = select_period(source.events, args.start_date, args.end_date)
        rules = _rules()
        accounts: list[dict] = []
        active = None
        active_record = None
        trace_rows: list[dict] = []
        consumed_trade_ids: list[str] = []
        global_trade_index = 0

        for event_index, event in enumerate(selected_events):
            if active is None:
                if len(accounts) >= args.max_attempts:
                    break
                account_id = f"evaluation-{len(accounts) + 1:02d}"
                active = AccountEngine(account_id, rules)
                active_record = {"account_id": account_id, "trades_consumed": 0,
                                 "applied_trades": 0, "dll_skipped_trades": 0,
                                 "terminal_ignored_trades": 0,
                                 "included_gross_pnl": Decimal("0"),
                                 "included_commissions": Decimal("0"),
                                 "first_trade_index": None, "last_trade_index": None}

            before = active.snapshot()
            if isinstance(event, CompletedTrade):
                global_trade_index += 1
                active_record["trades_consumed"] += 1
                active_record["first_trade_index"] = (active_record["first_trade_index"]
                                                       or global_trade_index)
                active_record["last_trade_index"] = global_trade_index
                consumed_trade_ids.append(event.trade_id)
                emitted = active.apply_trade(event)
                decisions = [row["type"] for row in emitted if row["type"] in
                             ("trade_applied", "trade_skipped", "trade_ignored")]
                require(len(decisions) == 1, f"Trade {event.trade_id} has {len(decisions)} dispositions")
                decision = decisions[0]
                if decision == "trade_applied":
                    active_record["applied_trades"] += 1
                    active_record["included_gross_pnl"] += event.gross_pnl
                    active_record["included_commissions"] += event.commission
                elif decision == "trade_skipped":
                    active_record["dll_skipped_trades"] += 1
                else:
                    active_record["terminal_ignored_trades"] += 1
                timestamp, source_order, session_id = event.exit_timestamp, event.source_order, event.session_id
                trade_id, gross, commission, net = (event.trade_id, str(event.gross_pnl),
                                                    str(event.commission), str(event.net_pnl))
                source_type = "completed_trade"
            else:
                emitted = active.close_session(event)
                decision = "session_close"
                timestamp, source_order, session_id = event.timestamp, event.source_order, event.session_id
                trade_id, gross, commission, net, source_type = "", "", "", "", "session_close"

            after = active.snapshot()
            terminals = [row for row in emitted if row["type"] in
                         ("account_breached", "evaluation_passed")]
            require(len(terminals) <= 1, "More than one terminal event for an account input")
            trace_rows.append({
                "event_index": event_index, "trade_index": global_trade_index if isinstance(event, CompletedTrade) else "",
                "account_id": before["account_id"], "source_event_type": source_type,
                "timestamp": timestamp.isoformat(), "source_order": source_order,
                "session_id": session_id, "trade_id": trade_id, "gross_pnl": gross,
                "commission": commission, "net_pnl": net,
                "decision_events": json.dumps([row["type"] for row in emitted]),
                "balance_before": before["balance"], "balance_after": after["balance"],
                "session_net_before": before["current_session_net_pnl"],
                "session_net_after": after["current_session_net_pnl"],
                "loss_floor_before": before["loss_floor"], "loss_floor_after": after["loss_floor"],
                "dll_locked_before": before["dll_locked"], "dll_locked_after": after["dll_locked"],
                "status_before": before["status"], "status_after": after["status"],
                "outcome": after["outcome"] or "active",
            })

            if terminals:
                active.finish_data()
                final = active.snapshot()
                require(Decimal(final["balance"]) == (rules.starting_capital
                        + active_record["included_gross_pnl"] - active_record["included_commissions"]),
                        f"Balance reconciliation failed for {active_record['account_id']}")
                require(final["trade_count"] == active_record["applied_trades"],
                        f"Applied trade count mismatch for {active_record['account_id']}")
                require(final["skipped_trades"] == active_record["dll_skipped_trades"],
                        f"Skipped trade count mismatch for {active_record['account_id']}")
                active_record.update({"outcome": final["status"], "ending_snapshot": final,
                                      "terminal_event": terminals[0]})
                accounts.append(active_record)
                active = active_record = None

        if active is not None:
            active.finish_data()
            final = active.snapshot()
            require(Decimal(final["balance"]) == (rules.starting_capital
                    + active_record["included_gross_pnl"] - active_record["included_commissions"]),
                    f"Balance reconciliation failed for unfinished {active_record['account_id']}")
            require(final["trade_count"] == active_record["applied_trades"],
                    f"Applied trade count mismatch for unfinished {active_record['account_id']}")
            require(final["skipped_trades"] == active_record["dll_skipped_trades"],
                    f"Skipped trade count mismatch for unfinished {active_record['account_id']}")
            active_record.update({"outcome": "unfinished", "ending_snapshot": final,
                                  "terminal_event": None})
            accounts.append(active_record)

        require(global_trade_index == len(consumed_trade_ids), "Trade index/accounting count mismatch")
        require(len(consumed_trade_ids) == len(set(consumed_trade_ids)), "A source trade was consumed more than once")
        require(len(consumed_trade_ids) <= period["trade_count"], "Consumed more trades than selected period contains")
        counts = {key: sum(account["outcome"] == key for account in accounts)
                  for key in ("passed", "breached", "unfinished")}
        require(sum(counts.values()) == len(accounts), "Cohort outcome counts do not sum to started accounts")

        with (output / "events.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(trace_rows)
        report_data = {
            "status": "passed", "checks": {
                "historical_validation_and_adapter_reconciliation": "passed",
                "every_consumed_trade_has_one_disposition": "passed",
                "source_trade_ids_are_unique_in_cohort": "passed",
                "per_account_balance_and_trade_counts_reconcile": "passed",
                "outcome_counts_sum_to_started_accounts": "passed"},
            "input_run_id": source.metadata["run_id"],
            "source_trade_count": source.validation["trade_count"],
            "selected_period": period,
            "consumed_trade_count": global_trade_index,
            "remaining_trade_count": period["trade_count"] - global_trade_index,
            "accounts_started": len(accounts), "outcome_counts": counts,
            "account_start_policy": "Fresh evaluation starts at the next source event after prior pass/breach.",
            "rules": {"starting_capital": "25000", "daily_loss_limit": "600",
                      "evaluation_target": "1250", "consistency_limit": "0.50",
                      "trailing_distance": "1000", "floor_cap": "25100",
                      "consistency_policy": "strict",
                      "commission_per_contract_per_side": str(config["commission_per_contract_per_side"])},
            "accounts": [{**account, "included_gross_pnl": str(account["included_gross_pnl"]),
                           "included_commissions": str(account["included_commissions"])}
                          for account in accounts],
            "adapter_validation": source.validation,
            "legacy_replay_result": source.legacy_result,
            "input_hashes": list(source.input_hashes),
            "debug_note": "Inspect events.csv in event_index order. Each row shows the account decision and financial state before/after the source trade or observed session close.",
            "limitations": ["Sequential evaluations only; funded continuation, fees, payouts, and slot limits are omitted.",
                            "Completed-trade checks exclude intratrade limit touches.",
                            "Final unobserved session is not force-closed.",
                            "Rules are explicit quick-test development assumptions."]}
        dump(output / "validation.json", report_data)
        rows = ["# Cohort simulation debug and validation", "",
                f"Validation checks: **passed**. Source run `{source.metadata['run_id']}`.",
                f"Selected period: {period['start_date_inclusive'] or 'start'} through {period['end_date_inclusive'] or 'end'} (inclusive session dates).",
                f"Trades consumed: {global_trade_index} / {period['trade_count']} selected trades (full source: {source.validation['trade_count']}).",
                f"Accounts: {len(accounts)}; passed {counts['passed']}, breached {counts['breached']}, unfinished {counts['unfinished']}.",
                "", "## Account by account", "",
                "| Attempt | Source trades | Trades used | Result | Ending balance | Net P&L |",
                "|---:|---:|---:|---|---:|---:|"]
        for account in accounts:
            snapshot = account["ending_snapshot"]
            span = (f"{account['first_trade_index']}–{account['last_trade_index']}"
                    if account["first_trade_index"] is not None else "—")
            rows.append(f"| {account['account_id']} | {span} | {account['trades_consumed']} | {account['outcome']} | ${snapshot['balance']} | ${snapshot['net_pnl']} |")
        rows += [
                "", "## Inspecting the trace", "",
                "Open `events.csv` and sort by `event_index` (already in source order). Each row records the account, source event, trade P&L, engine event names, balance, session P&L, floor, DLL lock, and status before and after processing.",
                "", "## Checks performed", "",
                "- Original inputs pass the existing historical validator and adapter reconciliation.",
                "- Every consumed trade receives exactly one engine disposition.",
                "- No source trade ID is consumed twice.",
                "- Each account balance equals starting capital plus applied gross P&L less applied commissions.",
                "- Account trade and DLL skip counters match the emitted dispositions.",
                "- Outcome totals sum to the number of accounts started.",
                "", "This checks implementation consistency and makes each decision inspectable; it does not prove that the provisional rule assumptions match provider rules. Funded continuation and payouts are outside this sequential debug run."]
        (output / "report.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(json.dumps({"status": "passed", "accounts_started": len(accounts),
                          "passed": counts["passed"], "breached": counts["breached"],
                          "unfinished": counts["unfinished"], "trace_rows": len(trace_rows),
                          "output": str(output.resolve())}))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        dump(output / "validation.json", {"status": "failed", "error": str(exc)})
        print(f"Cohort debug validation failed: {exc}\nReport: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
