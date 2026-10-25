"""Dependency-free, single-contract validation and provisional evaluation replay."""
import argparse
import csv
import hashlib
import heapq
import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REVISION = "0.1.0"
ZERO = Decimal(0)
TOL = Decimal("0.000001")
PROJECT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(value is not None and str(value).strip() != "", "Missing numeric value")
    result = Decimal(str(value))
    require(result.is_finite(), "Nonfinite numeric value")
    return result


def money(value):
    value = value.strip().replace("$", "").replace(",", "")
    return -number(value[1:-1]) if value.startswith("(") and value.endswith(")") else number(value)


def close(left, right, label):
    require(abs(left - right) <= TOL, f"{label}: {left} != {right}")


def stamp(value):
    # Python retains microseconds; logger strings are retained unchanged in reports.
    result = datetime.fromisoformat(re.sub(r"(\.\d{6})\d+(?=[+-]|Z|$)", r"\1", value))
    require(result.utcoffset() is not None, f"Unresolved timestamp offset: {value}")
    return result


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def rows(path, required):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None, f"Empty CSV: {path}")
        require(set(required) <= set(reader.fieldnames), f"Missing columns in {path}: {set(required) - set(reader.fieldnames)}")
        for index, row in enumerate(reader, 2):
            # Analyzer has a trailing unnamed empty column; never drop actual data.
            require(None not in row and None not in row.values(), f"Malformed CSV at {path}:{index}")
            yield row


def logger_rows(run, name, metadata, required):
    prior_seq, prior_time = -1, None
    for row in rows(run / f"{name}.csv", ["run_id", "instrument", "event_sequence", *required]):
        require(row["run_id"] == metadata["run_id"], f"Mixed run IDs in {name}")
        require(row["instrument"] == metadata["instrument"], f"Mixed instruments in {name}")
        seq = int(row["event_sequence"])
        require(seq > prior_seq, f"Nonincreasing sequence in {name}")
        prior_seq = seq
        if "timestamp" in row:
            instant = stamp(row["timestamp"])
            require(prior_time is None or instant >= prior_time, f"Time moves backwards in {name}")
            prior_time = instant
        if "trading_day" in row:
            datetime.strptime(row["trading_day"], "%Y-%m-%d")
        require("TimezoneUnresolved" not in row.get("data_quality", ""), f"Unresolved time in {name}")
        yield row


def load_config(path):
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    for key in ("starting_balance", "profit_target", "drawdown_distance", "locked_floor", "consistency_limit", "commission_per_contract_per_side"):
        config[key] = number(config[key])
    require(config["starting_balance"] > 0 and config["profit_target"] > 0, "Capital and target must be positive")
    require(0 < config["drawdown_distance"] < config["starting_balance"], "Invalid drawdown distance")
    require(config["locked_floor"] >= config["starting_balance"] - config["drawdown_distance"], "Invalid floor cap")
    require(0 < config["consistency_limit"] <= 1, "Invalid consistency ratio")
    require(config["commission_per_contract_per_side"] >= 0, "Negative costs")
    require(config["daily_loss_limit"] is None, "DLL-on is not supported in this version")
    require(config["contracts"] == 1, "Only one original contract is supported")
    require(config["source_timezone"] == "Eastern Standard Time", "This prototype supports the recorded Eastern source clock only")
    require(config["session_reset_source_hour"] == 18, "This prototype requires the explicit 18:00 source-clock scenario")
    require(config["purchase_fee"] is None or number(config["purchase_fee"]) >= 0, "Invalid purchase fee")
    snapshot = (path.parent / config["rules_snapshot"]).resolve()
    require(snapshot.is_file(), f"Missing rules snapshot: {snapshot}")
    config["rules_snapshot_path"] = str(snapshot)
    return config


def validate(run, analyzer_trades, analyzer_summary, config):
    metadata = json.loads((run / "run_metadata.json").read_text(encoding="utf-8-sig"))
    require(metadata["completion_status"] == "Finalized" and metadata["usable"] and metadata["accounting_complete"], "Run is not finalized with complete accounting")
    require(metadata.get("error") is None and metadata["schema_version"] == "1.0", "Run error or unsupported schema")
    require(metadata["instrument"].startswith("MNQ ") and number(metadata["point_value"]) == 2, "Only MNQ with $2 point value is supported")
    require(metadata["source_timezone"] == config["source_timezone"], "Source clock differs from configured clock")
    require(metadata["strategy_parameters"]["AllowLayering"].lower() == "false", "Layering must be disabled")
    require(metadata["initial_strategy_quantity"] == 0 and metadata["final_signed_position_quantity"] == 0 and not metadata["final_open_lots"], "Prototype requires a flat-start, flat-end run")
    point = number(metadata["point_value"])
    executions = list(logger_rows(run, "executions", metadata, ["timestamp", "execution_id", "execution_phase", "order_id", "account_name", "execution_side", "execution_quantity", "execution_price", "realized_pnl", "signed_position_quantity_after_execution", "average_position_price_after_execution", "position_quantity_after_execution"]))
    require(len(executions) == metadata["execution_count"] and executions, "Execution count mismatch/empty input")
    position, entry, gross, units = 0, None, ZERO, 0
    identities, by_seq, by_id = set(), {}, {}
    for row in executions:
        quantity = int(row["execution_quantity"])
        require(quantity == 1, "Only unit fills are supported")
        price = number(row["execution_price"])
        side = row["execution_side"]
        require(side in ("Buy", "BuyToCover", "Sell", "SellShort"), "Unknown execution side")
        delta = quantity if side in ("Buy", "BuyToCover") else -quantity
        require(row["execution_id"], "Missing execution ID")
        identity = tuple(row[k] for k in ("execution_phase", "instrument", "account_name", "order_id", "execution_id"))
        require(identity not in identities, "Duplicate execution identity")
        identities.add(identity)
        require(row["execution_id"] not in by_id, "Ambiguous execution ID across scopes; unsupported in this prototype")
        by_id[row["execution_id"]] = row
        expected = ZERO
        if position == 0:
            entry = price
        else:
            require(position + delta == 0, "Layered or reversing fill unsupported")
            expected = (price - entry) * position * point
            entry = None
        position += delta
        require(abs(position) <= 1, "Position exceeds one contract")
        require(position == int(row["signed_position_quantity_after_execution"]), "Inventory mismatch")
        require(abs(position) == int(row["position_quantity_after_execution"]), "Absolute inventory mismatch")
        if position:
            close(number(row["average_position_price_after_execution"]), entry, "Entry basis")
        else:
            require(not row["average_position_price_after_execution"], "Flat average price must be unavailable")
        close(number(row["realized_pnl"]), expected, "Fill P&L")
        gross += expected
        units += quantity
        by_seq[int(row["event_sequence"])] = row
    require(position == 0, "Execution ledger ends open")
    close(gross, number(metadata["final_gross_realized_pnl"]), "Metadata P&L")

    trades = list(logger_rows(run, "trades", metadata, ["trade_id", "entry_execution_id", "exit_execution_id", "entry_timestamp", "exit_timestamp", "direction", "quantity", "entry_price", "exit_price", "gross_realized_pnl", "entry_signal", "raw_exit_name"]))
    require(len(trades) == metadata["closed_segment_count"], "Closed-segment count mismatch")
    require(len({t["trade_id"] for t in trades}) == len(trades), "Duplicate trade IDs")
    used_entries, used_exits = set(), set()
    for trade in trades:
        require(trade["direction"] in ("Long", "Short") and int(trade["quantity"]) == 1, "Invalid segment side/quantity")
        first, last = by_id[trade["entry_execution_id"]], by_id[trade["exit_execution_id"]]
        require(first["execution_id"] not in used_entries and last["execution_id"] not in used_exits, "Fill reused by trade segments")
        used_entries.add(first["execution_id"])
        used_exits.add(last["execution_id"])
        require(stamp(trade["entry_timestamp"]) == stamp(first["timestamp"]) and stamp(trade["exit_timestamp"]) == stamp(last["timestamp"]), "Segment/fill time mismatch")
        require(stamp(trade["entry_timestamp"]) <= stamp(trade["exit_timestamp"]), "Exit precedes entry")
        require(int(first["event_sequence"]) < int(last["event_sequence"]) == int(trade["event_sequence"]), "Segment/fill sequence mismatch")
        require(int(first["signed_position_quantity_after_execution"]) == (1 if trade["direction"] == "Long" else -1) and int(last["signed_position_quantity_after_execution"]) == 0, "Segment/fill direction mismatch")
        close(number(trade["entry_price"]), number(first["execution_price"]), "Segment entry price")
        close(number(trade["exit_price"]), number(last["execution_price"]), "Segment exit price")
        pnl = (number(trade["exit_price"]) - number(trade["entry_price"])) * point * (1 if trade["direction"] == "Long" else -1)
        close(number(trade["gross_realized_pnl"]), pnl, "Trade P&L")
    require(len(used_entries | used_exits) == len(executions) == 2 * len(trades), "Not all fills belong to complete unit trades")
    close(sum((number(t["gross_realized_pnl"]) for t in trades), ZERO), gross, "Trade/fill P&L")

    analyzer = list(rows(analyzer_trades, ["Trade number", "Instrument", "Market pos.", "Qty", "Entry price", "Exit price", "Entry time", "Exit time", "Entry name", "Exit name", "Profit", "Commission", "Clearing Fee", "Exchange Fee", "IP Fee", "NFA Fee"]))
    analyzer.sort(key=lambda r: int(r["Trade number"]))
    require(len(analyzer) == len(trades), "Analyzer trade count mismatch")
    require([int(r["Trade number"]) for r in analyzer] == list(range(1, len(analyzer) + 1)), "Missing/duplicate Analyzer trade numbers")
    analyzer_net, analyzer_cost = ZERO, ZERO
    for index, (a, trade) in enumerate(zip(analyzer, trades), 1):
        for key_a, key_t in (("Instrument", "instrument"), ("Market pos.", "direction"), ("Entry name", "entry_signal"), ("Exit name", "raw_exit_name")):
            require(a[key_a] == trade[key_t], f"Analyzer trade {index}: {key_a} mismatch")
        require(int(a["Qty"]) == int(trade["quantity"]), f"Analyzer trade {index}: quantity mismatch")
        for key_a, key_t in (("Entry price", "entry_price"), ("Exit price", "exit_price")):
            close(number(a[key_a]), number(trade[key_t]), f"Analyzer trade {index}: {key_a}")
        for key_a, key_t in (("Entry time", "entry_timestamp"), ("Exit time", "exit_timestamp")):
            require(datetime.strptime(a[key_a], "%m/%d/%Y %H:%M:%S") == stamp(trade[key_t]).replace(tzinfo=None, microsecond=0), f"Analyzer trade {index}: {key_a} mismatch (assumes source-clock Analyzer display)")
        cost = sum((money(a[k]) for k in ("Commission", "Clearing Fee", "Exchange Fee", "IP Fee", "NFA Fee")), ZERO)
        require(cost == 0, "Current Analyzer reconciliation supports zero-cost reference exports only")
        close(money(a["Profit"]), number(trade["gross_realized_pnl"]), f"Analyzer trade {index}: profit")
        analyzer_net += money(a["Profit"])
        analyzer_cost += cost
    summary = {r["Performance"]: r for r in rows(analyzer_summary, ["Performance", "All trades"]) if r["Performance"]}
    close(money(summary["Total net profit"]["All trades"]), analyzer_net, "Analyzer summary net")
    close(money(summary["Commission"]["All trades"]), analyzer_cost, "Analyzer summary commissions")
    require(int(summary["Total # of trades"]["All trades"]) == len(trades), "Analyzer summary count mismatch")
    close(money(summary["Gross profit"]["All trades"]), sum((number(t["gross_realized_pnl"]) for t in trades if number(t["gross_realized_pnl"]) > 0), ZERO), "Gross wins")
    close(money(summary["Gross loss"]["All trades"]), sum((number(t["gross_realized_pnl"]) for t in trades if number(t["gross_realized_pnl"]) < 0), ZERO), "Gross losses")

    # Merge execution/equity streams by callback sequence, validating each observed ledger state.
    running_gross, position, average, running_cost = ZERO, 0, None, ZERO
    eq_count, prior_seq, prior_time = 0, -1, None
    daily, daily_gross = {}, {}
    previous_session = None
    observed_execution_sequences = set()
    equity_stream = logger_rows(run, "equity", metadata, ["timestamp", "signed_position_quantity", "average_position_price", "mark_price", "cumulative_gross_realized_pnl", "unrealized_pnl", "gross_equity_change", "observation_source"])
    for seq, kind, row in heapq.merge(((int(r["event_sequence"]), "execution", r) for r in executions), ((int(r["event_sequence"]), "equity", r) for r in equity_stream)):
        require(seq > prior_seq, "Cross-stream sequence collision")
        prior_seq = seq
        instant = stamp(row["timestamp"])
        require(prior_time is None or instant >= prior_time, "Combined event timestamps move backwards")
        prior_time = instant
        day = session_day(row["timestamp"], config)
        if previous_session is not None and day != previous_session:
            require(position == 0, "Overnight positions unsupported in the full input run")
        previous_session = day
        if kind == "execution":
            running_gross += number(row["realized_pnl"])
            running_cost += number(row["execution_quantity"]) * config["commission_per_contract_per_side"]
            position = int(row["signed_position_quantity_after_execution"])
            average = number(row["average_position_price_after_execution"]) if position else None
            daily[day] = daily.get(day, ZERO) + number(row["realized_pnl"]) - config["commission_per_contract_per_side"]
            daily_gross[day] = daily_gross.get(day, ZERO) + number(row["realized_pnl"])
        else:
            eq_count += 1
            require(position == int(row["signed_position_quantity"]), "Equity inventory differs from executions")
            if position:
                close(number(row["average_position_price"]), average, "Equity position basis")
            unrealized = (number(row["mark_price"]) - average) * position * point if position else ZERO
            close(number(row["unrealized_pnl"]), unrealized, "Equity unrealized P&L")
            close(number(row["cumulative_gross_realized_pnl"]), running_gross, "Equity realized P&L")
            close(number(row["gross_equity_change"]), running_gross + unrealized, "Equity gross change")
            if row["observation_source"] == "Execution":
                # Logger writes exactly one equity observation immediately after each fill.
                require(seq - 1 in by_seq, "Execution equity observation lacks corresponding fill")
                require(stamp(row["timestamp"]) == stamp(by_seq[seq - 1]["timestamp"]), "Execution equity timestamp differs from fill")
                observed_execution_sequences.add(seq - 1)
    require(eq_count > 0 and prior_seq == metadata["last_event_sequence"], "Missing final equity observation")
    require(eq_count == metadata["bar_count"] + len(executions) + metadata["last_tick_count"], "Equity observation count differs from bar/fill/tick counts")
    require(observed_execution_sequences == set(by_seq), "Missing execution equity observations")
    close(running_gross, gross, "Ending equity realized P&L")
    trade_daily = {}
    for trade in trades:
        day = session_day(trade["exit_timestamp"], config)
        trade_daily[day] = trade_daily.get(day, ZERO) + number(trade["gross_realized_pnl"])
    for day in daily_gross.keys() | trade_daily.keys():
        close(daily_gross.get(day, ZERO), trade_daily.get(day, ZERO), f"Daily execution/trade P&L {day}")
    bar_count = 0
    first_bar, last_bar = None, None
    for row in logger_rows(run, "bars", metadata, ["timestamp", "open", "high", "low", "close", "volume"]):
        bar_count += 1
        first_bar = first_bar or row["timestamp"]
        last_bar = row["timestamp"]
        op, hi, lo, cl = [number(row[k]) for k in ("open", "high", "low", "close")]
        require(lo <= min(op, cl) <= max(op, cl) <= hi and number(row["volume"]) >= 0, "Invalid OHLC/volume")
    require(bar_count == metadata["bar_count"], "Bar count mismatch")
    require(stamp(first_bar) == stamp(metadata["observed_start"]) and stamp(last_bar) == stamp(metadata["observed_end"]), "Observed range mismatch")
    return metadata, executions, {
        "status": "passed", "run_id": metadata["run_id"], "trade_count": len(trades), "execution_count": len(executions),
        "equity_observations": eq_count, "bar_count": bar_count, "gross_pnl": gross,
        "analyzer_net_pnl": analyzer_net, "analyzer_commissions_and_fees": analyzer_cost,
        "assumed_commissions_full_run": running_cost, "net_pnl_under_fixed_cost_assumption_full_run": gross - running_cost,
        "daily_net_pnl_under_assumption": daily, "daily_gross_pnl": daily_gross,
        "limitations": ["Analyzer timestamps assumed to use the logger source wall clock; compared to second precision.",
                        "Commissions are unknown in the logger and zero in Analyzer; fixed costs are a separate scenario assumption.",
                        "Validation does not establish continuous intrabar coverage or full platform acceptance."],
    }


def session_day(timestamp, config):
    local = stamp(timestamp)
    # Input offsets encode DST. Validate Eastern wall clock offsets without a Windows tzdata dependency.
    require(local.utcoffset() in (timedelta(hours=-5), timedelta(hours=-4)), "Unexpected source-clock offset")
    return (local.date() + timedelta(days=int(local.hour >= config["session_reset_source_hour"]))).isoformat()


def simulate(observations, config):
    start = config["starting_balance"]
    balance = equity = start
    floor = start - config["drawdown_distance"]
    peak_close = start
    session_start, session = start, None
    best_day, completed_sessions = ZERO, 0
    events = []
    position, last = 0, None
    status = "incomplete"

    def event(kind, row, **extra):
        events.append({"event": kind, "timestamp": row["timestamp"], "event_sequence": row["event_sequence"],
                       "session": session, "balance": balance, "equity": equity, "loss_floor": floor, **extra})

    for row in observations:
        day = session_day(row["timestamp"], config)
        if session is None:
            require(int(row["position"]) == 0, "Replay must begin with a flat observation")
            session = day
            event("evaluation_started", row)
        elif day != session:
            require(day > session, "Session goes backwards")
            require(position == 0, "Overnight positions unsupported")
            completed_sessions += 1
            day_profit = balance - session_start
            best_day = max(best_day, day_profit)
            peak_close = max(peak_close, balance)
            floor = max(floor, min(config["locked_floor"], peak_close - config["drawdown_distance"]))
            profit = balance - start
            ratio = best_day / profit if profit > 0 else None
            event("session_closed", last, day_net=day_profit, best_winning_day=best_day, consistency_ratio=ratio)
            if equity <= floor:
                status = "breach"
                event("breach_after_eod_floor_update", last)
                break
            if profit >= config["profit_target"] and ratio <= config["consistency_limit"]:
                status = "pass"
                event("evaluation_passed_at_session_end", last, consistency_ratio=ratio)
                break
            session, session_start = day, balance
        balance = start + number(row["gross_realized"]) - number(row["costs"])
        equity = balance + number(row["unrealized"])
        position = int(row["position"])
        require(abs(position) <= 1, "Replay position exceeds one")
        if row["source"] == "Execution":
            event("execution_observed", row, position=position)
        if equity <= floor:
            status = "breach"
            event("observed_equity_breach", row, position=position)
            last = row
            break
        last = row
    require(last is not None, "No observations")
    if status == "incomplete":
        event("data_ended_without_pass_or_observed_breach", last, final_session_unclosed=True)
    return {
        "outcome": status, "confidence": "provisional_observed_samples_only", "ending_timestamp": last["timestamp"],
        "ending_balance": balance, "ending_observed_equity": equity, "loss_floor": floor,
        "completed_sessions": completed_sessions, "largest_completed_winning_day": best_day,
        "position_at_stop": position, "purchase_fee": config["purchase_fee"], "net_cash_profit": None,
        "interpretation": "One attempt from input start. Missing intrabar observations may hide an earlier breach; no actual liquidation is synthesized. A pass is sampled eligibility, not proof of account survival.",
    }, events


def replay_rows(run, metadata, executions, config):
    costs = ZERO
    index = 0
    # Equity rows follow execution rows and include their actual observed mark.
    for row in logger_rows(run, "equity", metadata, ["timestamp"]):
        sequence = int(row["event_sequence"])
        while index < len(executions) and int(executions[index]["event_sequence"]) < sequence:
            costs += number(executions[index]["execution_quantity"]) * config["commission_per_contract_per_side"]
            index += 1
        yield {"timestamp": row["timestamp"], "event_sequence": sequence, "position": row["signed_position_quantity"],
               "gross_realized": row["cumulative_gross_realized_pnl"], "unrealized": row["unrealized_pnl"],
               "costs": costs, "source": row["observation_source"]}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "replay"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--analyzer-trades", type=Path, required=True)
    parser.add_argument("--analyzer-summary", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "configs/lucidflex_25k_provisional.json")
    parser.add_argument("--out", type=Path, help="New output directory; existing folders are never overwritten")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    version = config["strategy_version"]
    require(version in ("v0.1",), "Unknown strategy version; add a source/run manifest before using it")
    output = args.out or PROJECT / "simulation-results" / version / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    try:
        metadata, executions, validation = validate(args.run, args.analyzer_trades, args.analyzer_summary, config)
        manifest_path = PROJECT / "versions" / version / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        require(manifest["strategy_version"] == version and any(r["run_id"] == metadata["run_id"] for r in manifest["runs"]), "Run ID is not registered under the configured strategy version")
        snapshots = []
        for entry in manifest["source_snapshot"]:
            source = manifest_path.parent / entry["file"]
            require(digest(source).lower() == entry["sha256"].lower(), "Preserved source snapshot hash mismatch")
            snapshots.append(source)
        source_paths = [args.run / name for name in ("run_metadata.json", "executions.csv", "trades.csv", "equity.csv", "bars.csv")]
        source_paths += [args.analyzer_trades, args.analyzer_summary, args.config, Path(config["rules_snapshot_path"]), Path(__file__), manifest_path, *snapshots]
        provenance = {"simulator_revision": REVISION, "strategy_version": version, "run_id": metadata["run_id"],
                      "inputs": [{"path": str(p.resolve()), "sha256": digest(p)} for p in source_paths], "config": config}
        dump(output / "provenance.json", provenance)
        dump(output / "validation.json", validation)
        result, events = ({}, [])
        if args.command == "replay":
            result, events = simulate(replay_rows(args.run, metadata, executions, config), config)
            dump(output / "result.json", result)
            fields = list(dict.fromkeys(k for event in events for k in event))
            with (output / "events.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(events)
        report = ["# v0.1 validation and evaluation replay", "", f"Input run: `{metadata['run_id']}`.", "",
                  f"Validation: passed. {validation['trade_count']} trades; {validation['execution_count']} executions.",
                  f"Gross P&L: ${validation['gross_pnl']}; Analyzer net P&L with zero costs: ${validation['analyzer_net_pnl']}.",
                  f"Full-run assumed commissions: ${validation['assumed_commissions_full_run']}; full-run net after assumed costs: ${validation['net_pnl_under_fixed_cost_assumption_full_run']}.", ""]
        if result:
            report += [f"Provisional one-attempt outcome: **{result['outcome']}** at {result['ending_timestamp']}.",
                       f"Observed equity at stop: ${result['ending_observed_equity']}; loss floor: ${result['loss_floor']}.",
                       "Replay stops at the first sampled breach/pass; full-run P&L above is a separate validation statistic.", ""]
        report += ["## Scenario assumptions", "", *[f"- {item}" for item in config["assumptions"]], "",
                   "Intrabar survival cannot be certified. This is one historical attempt, not a pass-rate estimate or a prediction.",
                   "Input hashes, resolved configuration, daily net totals, and event details are in the accompanying JSON/CSV files."]
        (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print(json.dumps({"validation": "passed", "outcome": result.get("outcome"), "output": str(output.resolve())}))
        return 0
    except (ValueError, KeyError, OSError, InvalidOperation) as error:
        dump(output / "validation.json", {"status": "failed", "error": str(error)})
        print(f"Validation/replay failed: {error}\nReport: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
