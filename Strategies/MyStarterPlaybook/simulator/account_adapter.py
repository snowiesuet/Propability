"""Validated completed-trade/session adapter and independent account checks.

Price observations establish session transitions only. Loss checks consume
completed trades. No final close, missing calendar day, or liquidation is made up.
"""

import heapq
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from account_engine import AccountEngine, AccountRules, CompletedTrade, SessionClose
from replay import (digest, logger_rows, number, replay_rows, require, rows,
                    session_day, simulate, stamp, validate)


ZERO = Decimal("0")


@dataclass(frozen=True)
class AccountInput:
    metadata: dict
    validation: dict
    events: tuple[CompletedTrade | SessionClose, ...]
    observed_sessions: tuple[str, ...]
    legacy_result: dict
    input_hashes: tuple[dict, ...]


def load_account_input(run: Path, analyzer_trades: Path, analyzer_summary: Path,
                       validation_config: dict, commission_per_side: Decimal) -> AccountInput:
    """Fully validate Analyzer/logger accounting before exposing engine input.

    The legacy validation config supplies source clock and cost validation only;
    its DLL-off/40% account rules do not configure the completed-trade engines.
    Synthetic source orders reserve even numbers for original callbacks and odd
    numbers for the close inferred just before a new-session callback.
    """
    require(isinstance(commission_per_side, Decimal) and commission_per_side.is_finite()
            and commission_per_side >= ZERO, "Commission must be a finite nonnegative Decimal")
    require(commission_per_side == validation_config["commission_per_contract_per_side"],
            "Adapter and validation commission assumptions differ")
    paths = [run / name for name in ("run_metadata.json", "executions.csv", "trades.csv",
                                     "equity.csv", "bars.csv")]
    paths += [analyzer_trades, analyzer_summary]
    hashes = tuple({"path": str(p.resolve()), "sha256": digest(p)} for p in paths)
    metadata, executions, validation = validate(run, analyzer_trades, analyzer_summary, validation_config)
    trades = list(logger_rows(run, "trades", metadata, []))
    by_exit = {}
    for index, row in enumerate(trades):
        # Prove each segment is precisely one complete position, not a partial
        # segment from a larger position or a reused/reversing execution.
        first, last = executions[2 * index:2 * index + 2]
        require(row["entry_execution_id"] == first["execution_id"]
                and row["exit_execution_id"] == last["execution_id"],
                "Trade must match consecutive flat-to-flat execution pair")
        require(abs(int(first["signed_position_quantity_after_execution"])) == 1
                and int(last["signed_position_quantity_after_execution"]) == 0,
                "Trade does not represent a complete one-contract position")
        day = session_day(row["exit_timestamp"], validation_config)
        require(session_day(row["entry_timestamp"], validation_config) == day,
                "Completed trade crosses a session boundary")
        seq = int(row["event_sequence"])
        require(seq not in by_exit, "Multiple trade segments at one exit are unsupported")
        by_exit[seq] = CompletedTrade(
            row["trade_id"], stamp(row["entry_timestamp"]), stamp(row["exit_timestamp"]),
            day, seq * 2, int(row["quantity"]), number(row["gross_realized_pnl"]),
            (number(first["execution_quantity"]) + number(last["execution_quantity"])) * commission_per_side)

    events, sessions = [], []
    current = None
    equity = logger_rows(run, "equity", metadata, ["timestamp"])
    callbacks = heapq.merge(((int(r["event_sequence"]), r) for r in executions),
                           ((int(r["event_sequence"]), r) for r in equity), key=lambda item: item[0])
    for seq, row in callbacks:
        day = session_day(row["timestamp"], validation_config)
        if day != current:
            if current is not None:
                require(day > current, "Session labels go backwards")
                # Timestamp is when closure first becomes observable, not an
                # invented exchange close or the last mark of the previous day.
                events.append(SessionClose(current, stamp(row["timestamp"]), seq * 2 - 1))
            current = day
            sessions.append(day)
        if seq in by_exit:
            events.append(by_exit.pop(seq))
    require(not by_exit, "Missing completed-trade callback")
    require(sessions, "No observed sessions")
    # Exercise every converted event even when a study account would stop early.
    # A zero-floor development account cannot prove this for arbitrary losses;
    # use the pure ledger for accounting and stream checks below instead.
    from account_engine import AccountLedger
    ledger = AccountLedger("adapter-validation", Decimal("25000"))
    last_order, last_time, closed, active = -1, None, set(), None
    for event in events:
        instant = event.exit_timestamp if isinstance(event, CompletedTrade) else event.timestamp
        require(event.source_order > last_order and (last_time is None or instant >= last_time),
                "Converted stream is out of order")
        require(event.session_id not in closed, "Converted event belongs to a closed session")
        require(active is None or active == event.session_id, "Converted stream missed a session close")
        if isinstance(event, CompletedTrade):
            require(last_time is None or event.entry_timestamp >= last_time,
                    "Trade overlaps an inferred session close")
            ledger.apply_trade(event)
            active = event.session_id
        else:
            closed.add(event.session_id)
            active = None
        last_order, last_time = event.source_order, instant
    totals = ledger.snapshot()
    require(number(totals["gross_pnl"]) == validation["gross_pnl"], "Adapter gross P&L mismatch")
    require(number(totals["commissions"]) == validation["assumed_commissions_full_run"],
            "Adapter commission mismatch")
    require(number(totals["net_pnl"]) == validation["net_pnl_under_fixed_cost_assumption_full_run"],
            "Adapter full-run net mismatch")
    legacy, _ = simulate(replay_rows(run, metadata, executions, validation_config), validation_config)
    require(all(digest(Path(item["path"])) == item["sha256"] for item in hashes),
            "Input changed during validation")
    return AccountInput(metadata, validation, tuple(events), tuple(sessions), legacy, hashes)


def check_account(source: AccountInput, account_id: str, rules: AccountRules) -> dict:
    """Reconcile all applied/skipped/ignored trades independently of balances."""
    engine = AccountEngine(account_id, rules)
    audit = []
    groups = {name: [] for name in ("trade_applied", "trade_skipped", "trade_ignored")}
    terminal = None
    for event in source.events:
        new = (engine.apply_trade(event) if isinstance(event, CompletedTrade)
               else engine.close_session(event))
        audit.extend(new)
        if isinstance(event, CompletedTrade):
            decisions = [item for item in new if item["type"] in groups]
            require(len(decisions) == 1, "Trade must have exactly one accounting disposition")
            groups[decisions[0]["type"]].append(event)
        if terminal is None:
            terminal = next((item for item in new if item["type"] in
                             ("account_breached", "evaluation_passed")), None)
    audit.extend(engine.finish_data())
    snapshot = engine.snapshot()
    applied = groups["trade_applied"]
    gross = sum((trade.gross_pnl for trade in applied), ZERO)
    fees = sum((trade.commission for trade in applied), ZERO)
    require(number(snapshot["balance"]) == rules.starting_capital + gross - fees,
            "Account balance does not reconcile to included trades")
    require(number(snapshot["gross_pnl"]) == gross and number(snapshot["commissions"]) == fees,
            "Account gross/commissions do not reconcile")
    require(snapshot["trade_count"] == len(applied)
            and snapshot["skipped_trades"] == len(groups["trade_skipped"]), "Account count mismatch")
    require(sum(len(group) for group in groups.values()) == source.validation["trade_count"],
            "Not all source trades accounted for")
    session_net = {}
    for trade in applied:
        session_net[trade.session_id] = session_net.get(trade.session_id, ZERO) + trade.net_pnl
    require({day: number(net) for day, net in snapshot["session_net_pnl"].items()} == session_net,
            "Account session totals do not reconcile")
    for event in audit:
        if event["type"] == "session_closed":
            require(number(event["session_net_pnl"]) == session_net.get(event["session_id"], ZERO),
                    "Completed session total mismatch")
    return {"snapshot": snapshot, "terminal_event": terminal, "events": audit,
            "reconciliation": {"status": "passed", "applied_trade_count": len(applied),
                "dll_skipped_trade_count": len(groups["trade_skipped"]),
                "terminal_ignored_trade_count": len(groups["trade_ignored"]),
                "included_gross_pnl": str(gross), "included_commissions": str(fees),
                "included_net_pnl": str(gross - fees),
                "skipped_source_net_pnl": str(sum((t.net_pnl for t in groups["trade_skipped"]), ZERO)),
                "ignored_source_net_pnl": str(sum((t.net_pnl for t in groups["trade_ignored"]), ZERO))}}
