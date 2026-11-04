"""Run the selected sequential 50-purchase LucidFlex lifecycle study.

This is a completed-trade historical model. It preserves the older replay and
the evaluation-only cohort runner as separate tools.
"""

import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from account_adapter import load_account_input
from account_engine import CompletedTrade, SessionClose
from live_stage import LiveStage
from lifecycle_dashboard import write_dashboard
from replay import dump, load_config
from study_period import select_period


PROJECT = Path(__file__).resolve().parents[1]
SIMULATOR = Path(__file__).resolve().parent
D = Decimal
ZERO = D("0")


class SimAccount:
    """Lifecycle-specific simulation state; one source trade per account."""

    def __init__(self, account_id, attempt, stage, activation_index, purchase_fee=ZERO):
        self.account_id = account_id
        self.attempt = attempt
        self.stage = stage
        self.activation_index = activation_index
        self.status = "active"
        self.starting_balance = D("25000")
        self.balance = self.starting_balance
        self.floor = D("24000")
        self.highest_close = self.starting_balance
        self.dll = D("600")
        self.session_id = None
        self.session_net = ZERO
        self.session_payout_profit = ZERO
        self.dll_locked = False
        self.best_day = ZERO
        self.eval_target = D("1250")
        self.qualifying_days = 0
        self.cycle_profit = ZERO
        self.payout_count = 0
        self.payouts = []
        self.purchase_fee = purchase_fee
        self.trade_count = 0
        self.continuation_trades = 0
        self.reversal_trades = 0
        self.applied_gross = ZERO
        self.applied_commission = ZERO
        self.applied_net = ZERO
        self.wins = self.losses = self.breakevens = 0
        self.winning_net = ZERO
        self.losing_net = ZERO
        self.current_scaling_tier = "10 micros"
        self.events = []
        self.terminal_reason = None
        self.live = None
        self.start_day = activation_index + 1
        self.start_session_id = None
        self.end_day = None
        self.end_session_id = None
        self.duration_trading_sessions = None

    def start_session(self, session_id):
        if self.session_id == session_id:
            return
        self.session_id = session_id
        self.session_net = ZERO
        self.session_payout_profit = ZERO
        self.dll_locked = False

    def apply_trade(self, trade):
        self.start_session(trade.session_id)
        if self.dll_locked:
            self.events.append({"type": "trade_skipped", "trade_id": trade.trade_id,
                                "reason": "daily_loss_limit", "session_id": trade.session_id})
            return
        net = trade.net_pnl
        before = self.balance
        self.balance += net
        self.session_net += net
        self.session_payout_profit += net
        self.applied_gross += trade.gross_pnl
        self.applied_commission += trade.commission
        self.applied_net += net
        self.trade_count += 1
        signal = (trade.entry_signal or "").upper()
        if signal.startswith("CONT"):
            self.continuation_trades += 1
        elif signal.startswith("REV"):
            self.reversal_trades += 1
        if net > ZERO:
            self.wins += 1
            self.winning_net += net
        elif net < ZERO:
            self.losses += 1
            self.losing_net += net
        else:
            self.breakevens += 1
        if self.stage == "funded":
            self.cycle_profit += net
        self.events.append({"type": "trade_applied", "trade_id": trade.trade_id,
                            "session_id": trade.session_id, "net_pnl": str(net),
                            "entry_signal": trade.entry_signal,
                            "balance_before": str(before), "balance_after": str(self.balance)})
        if self.balance <= self.floor:
            self.status = "breached"
            self.terminal_reason = "max_loss_limit"
            self.events.append({"type": "account_breached", "balance": str(self.balance),
                                "floor": str(self.floor), "trade_id": trade.trade_id})
        elif self.session_net <= -self.dll:
            self.dll_locked = True
            self.events.append({"type": "dll_locked", "session_id": trade.session_id,
                                "session_net": str(self.session_net)})

    def close_session(self, event):
        if self.status != "active":
            return
        if self.session_id is None:
            self.session_id = event.session_id
            self.session_net = ZERO
        if self.session_id != event.session_id:
            raise ValueError(f"{self.account_id}: session close out of order")
        self.best_day = max(self.best_day, self.session_net)
        self.highest_close = max(self.highest_close, self.balance)
        old_floor = self.floor
        self.floor = max(old_floor, min(D("25100"), self.highest_close - D("1000")))
        self.events.append({"type": "session_closed", "session_id": event.session_id,
                            "session_net": str(self.session_net), "balance": str(self.balance),
                            "old_floor": str(old_floor), "new_floor": str(self.floor)})
        if self.balance <= self.floor:
            self.status = "breached"
            self.terminal_reason = "max_loss_limit_at_session_close"
            return
        if self.stage == "evaluation":
            profit = self.balance - self.starting_balance
            # Study policy: strict 50% consistency, without the published cushion.
            if profit >= self.eval_target and profit > ZERO and self.best_day <= D("0.50") * profit:
                self.status = "passed"
                self.terminal_reason = "evaluation_passed"
                self.events.append({"type": "evaluation_passed", "net_profit": str(profit),
                                    "largest_day": str(self.best_day)})
        elif self.stage == "funded":
            if self.session_net >= D("100"):
                self.qualifying_days += 1
            # Scaling changes only at session close. One MNQ remains within the
            # published first funded tier; source trades are never quantity-scaled.
            profit = self.balance - self.starting_balance
            self.current_scaling_tier = "20 micros" if profit >= D("1000") else "10 micros"
            self.events.append({"type": "funded_day_closed", "qualifying_days": self.qualifying_days,
                                "cycle_profit": str(self.cycle_profit),
                                "max_micros": 20 if self.current_scaling_tier == "20 micros" else 10})

    def payout_if_eligible(self, session_id, timestamp):
        if self.stage != "funded" or self.status != "active" or self.payout_count >= 5:
            return None
        if self.qualifying_days < 5 or self.cycle_profit <= ZERO or self.session_net <= ZERO:
            return None
        gross = min(self.cycle_profit * D("0.50"), D("1000"))
        if gross < D("500") or gross > self.session_payout_profit:
            return None
        old_floor = self.floor
        self.floor = D("25100")
        before = self.balance
        self.balance -= gross
        self.payout_count += 1
        receipt = gross * D("0.90")
        payout = {"type": "payout", "account_id": self.account_id,
                  "payout_number": self.payout_count, "session_id": session_id,
                  "timestamp": timestamp.isoformat(), "gross_request": str(gross),
                  "trader_receipt": str(receipt), "firm_share": str(gross - receipt),
                  "balance_before": str(before), "balance_after": str(self.balance),
                  "old_floor": str(old_floor), "locked_floor": str(self.floor),
                  "cycle_profit_before_request": str(self.cycle_profit)}
        self.payouts.append(payout)
        self.events.append(payout)
        self.cycle_profit = ZERO
        self.qualifying_days = 0
        self.session_payout_profit = ZERO
        funded_profit_after_payout = self.balance - self.starting_balance
        self.current_scaling_tier = "20 micros" if funded_profit_after_payout >= D("1000") else "10 micros"
        if self.balance <= self.floor:
            self.status = "breached"
            self.terminal_reason = "payout_left_balance_at_or_below_locked_floor"
        return payout

    def snapshot(self):
        avg_win = self.winning_net / self.wins if self.wins else None
        avg_loss = self.losing_net / self.losses if self.losses else None
        return {"account_id": self.account_id, "attempt": self.attempt, "stage": self.stage,
                "status": self.status, "terminal_reason": self.terminal_reason,
                "balance": str(self.balance), "loss_floor": str(self.floor),
                "highest_eod_balance": str(self.highest_close),
                "trade_count": self.trade_count, "gross_pnl": str(self.applied_gross),
                "continuation_trades": self.continuation_trades,
                "reversal_trades": self.reversal_trades,
                "commissions": str(self.applied_commission), "net_pnl": str(self.applied_net),
                "wins": self.wins, "losses": self.losses, "breakevens": self.breakevens,
                "win_rate": _percent(self.wins, self.trade_count),
                "average_win": str(avg_win) if avg_win is not None else None,
                "average_loss": str(avg_loss) if avg_loss is not None else None,
                "realized_reward_risk": str((avg_win / abs(avg_loss)).quantize(D("0.01")))
                    if avg_win is not None and avg_loss is not None else None,
                "qualifying_days_current_cycle": self.qualifying_days,
                "cycle_profit": str(self.cycle_profit), "payout_count": self.payout_count,
                "payouts": self.payouts, "max_micros_current_tier": self.current_scaling_tier,
                "purchase_fee": str(self.purchase_fee),
                "start_session": self.start_session_id, "end_session": self.end_session_id,
                "duration_trading_sessions": self.duration_trading_sessions,
                "events": self.events}


def _percent(n, d):
    return str((D(n) / D(d) * D("100")).quantize(D("0.1"))) + "%" if d else "N/A"


def _record_duration(account, end_day, end_session_id):
    if account.duration_trading_sessions is not None:
        return
    account.end_day = end_day
    account.end_session_id = end_session_id
    account.duration_trading_sessions = max(0, end_day - account.start_day + 1)


def _duration_summary(values):
    if not values:
        return "N/A (n=0)"
    average = (D(sum(values)) / D(len(values))).quantize(D("0.1"))
    return f"mean {average}; range {min(values)}–{max(values)} trading sessions; n={len(values)}"


def _trade_profile(events, event_type, duration_sessions=None):
    applied = [event for event in events if event.get("type") == event_type]
    pnls = [D(event["net_pnl"]) for event in applied]
    wins = [pnl for pnl in pnls if pnl > ZERO]
    losses = [pnl for pnl in pnls if pnl < ZERO]
    average_win = sum(wins, ZERO) / len(wins) if wins else None
    average_loss = sum(losses, ZERO) / len(losses) if losses else None
    signals = [(event.get("entry_signal") or "").upper() for event in applied]
    cont = sum(signal.startswith("CONT") for signal in signals)
    rev = sum(signal.startswith("REV") for signal in signals)
    trade_days = len({event.get("session_id") for event in applied if event.get("session_id")})
    observed_days = duration_sessions if duration_sessions is not None else trade_days
    return {"trade_count": len(pnls), "wins": len(wins), "losses": len(losses),
            "continuation_trades": cont, "reversal_trades": rev,
            "other_signal_trades": len(pnls) - cont - rev,
            "trading_days_with_trades": trade_days,
            "stage_trading_days": observed_days,
            "trades_per_trading_day": str((D(len(pnls)) / D(observed_days)).quantize(D("0.01"))) if observed_days else "0.00",
            "breakevens": sum(pnl == ZERO for pnl in pnls),
            "net_pnl": str(sum(pnls, ZERO)), "win_rate": _percent(len(wins), len(pnls)),
            "average_win": str(average_win) if average_win is not None else None,
            "average_loss": str(average_loss) if average_loss is not None else None,
            "realized_reward_risk": str((average_win / abs(average_loss)).quantize(D("0.01")))
                if average_win is not None and average_loss is not None else None}


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_lifecycle(source, events, period, max_attempts, purchase_fee):
    accounts = []
    funded = []
    live_accounts = []
    cash_ledger = []
    active_eval = None
    pending_activation = None
    next_eval_after_session = None
    total_spend = ZERO
    promotion = None
    trade_stats = {"wins": 0, "losses": 0, "breakevens": 0,
                   "winning_net": ZERO, "losing_net": ZERO}
    evaluation_pass_durations = []
    evaluation_breach_durations = []
    funded_duration_values = []
    first_payout_durations = []
    session_ordinals = {session: ordinal for ordinal, session in enumerate(
        sorted({item.session_id for item in events}), start=1)}
    source_sessions = {session: {"session_id": session, "trade_count": 0, "wins": 0,
                                  "losses": 0, "breakevens": 0, "gross_pnl": ZERO,
                                  "commissions": ZERO, "net_pnl": ZERO}
                       for session in session_ordinals}
    purchase_count = 0

    for index, event in enumerate(events):
        session_ordinal = session_ordinals[event.session_id]
        if isinstance(event, CompletedTrade):
            pnl = event.net_pnl
            row = source_sessions[event.session_id]
            row["trade_count"] += 1
            row["gross_pnl"] += event.gross_pnl
            row["commissions"] += event.commission
            row["net_pnl"] += pnl
            if pnl > ZERO:
                trade_stats["wins"] += 1; trade_stats["winning_net"] += pnl
                row["wins"] += 1
            elif pnl < ZERO:
                trade_stats["losses"] += 1; trade_stats["losing_net"] += pnl
                row["losses"] += 1
            else:
                trade_stats["breakevens"] += 1
                row["breakevens"] += 1

        # Funded activation is effective from the first event after a pass.
        if (pending_activation is not None and index >= pending_activation["activation_index"]
                and isinstance(event, CompletedTrade)):
            eval_account = pending_activation["evaluation"]
            f = SimAccount(f"funded-{eval_account.attempt:02d}", eval_account.attempt,
                           "funded", index)
            f.activation_day = session_ordinal
            f.start_day = session_ordinal
            f.start_session_id = event.session_id
            funded.append(f); accounts.append(f)
            pending_activation = None

        # Start each replacement evaluation on the next source event, preserving
        # the one-active-evaluation and no-rewind protocol.
        if (active_eval is None and purchase_count < max_attempts and promotion is None
                and isinstance(event, CompletedTrade)
                and (next_eval_after_session is None or event.session_id > next_eval_after_session)):
            purchase_count += 1
            active_eval = SimAccount(f"evaluation-{purchase_count:02d}", purchase_count,
                                     "evaluation", index, purchase_fee)
            active_eval.start_day = session_ordinal
            active_eval.start_session_id = event.session_id
            accounts.append(active_eval)
            total_spend += purchase_fee
            cash_ledger.append({"type": "evaluation_purchase", "account_id": active_eval.account_id,
                                "attempt": purchase_count, "timestamp": (
                                    event.entry_timestamp.isoformat()), "amount": str(-purchase_fee)})

        current = [a for a in [active_eval, *funded] if a is not None and a.status == "active"
                   and a.activation_index <= index]
        current += [l for l in live_accounts if l.status == "active"]
        for account in current:
            if account.stage == "live":
                if isinstance(event, CompletedTrade):
                    account.live.apply_trade(event.session_id, event.net_pnl, event.entry_signal)
                elif account.live.session_id == event.session_id:
                    account.live.close_session(event.session_id)
                    if (account.live.status == "active" and account.live.snapshot()["bonus_eligible"]
                            and not account.live.snapshot()["bonus_claimed"]):
                        bonus = account.live.claim_bonus()
                        cash_ledger.append({"type": "live_bonus_receipt", "account_id": account.account_id,
                                            "timestamp": event.timestamp.isoformat(),
                                            "amount": bonus["trader_receipt"], "gross": bonus["gross"]})
                account.status = account.live.status
                if account.status == "breached":
                    _record_duration(account, session_ordinal, event.session_id)
                continue
            if isinstance(event, CompletedTrade):
                account.apply_trade(event)
            else:
                account.close_session(event)
                if account.stage == "evaluation" and account.status == "passed":
                    account.passed_index = index
                    # Create funded state after the pass, available from next event.
                    pending_activation = {"evaluation": account, "activation_index": index + 1}
                if account.stage == "evaluation" and account.status == "breached":
                    next_eval_after_session = event.session_id
            if account.stage == "funded":
                payout_time = (event.exit_timestamp if isinstance(event, CompletedTrade)
                               else event.timestamp)
                payout = account.payout_if_eligible(event.session_id, payout_time)
                if payout:
                    cash_ledger.append({"type": "funded_payout_receipt", "account_id": account.account_id,
                                        "timestamp": payout_time.isoformat(),
                                        "payout_number": account.payout_count,
                                        "gross": payout["gross_request"],
                                        "amount": payout["trader_receipt"]})
                    if account.payout_count == 1 and not hasattr(account, "first_payout_index"):
                        account.first_payout_index = index
                        first_payout_durations.append(session_ordinal - account.activation_day + 1)
                    if account.payout_count == 5:
                        promotion = {"index": index, "timestamp": payout_time.isoformat(),
                                     "trigger_account_id": account.account_id}
                if account.status == "breached":
                    _record_duration(account, session_ordinal, event.session_id)
            if isinstance(event, SessionClose):
                account.session_id = None
                account.session_net = ZERO
                account.session_payout_profit = ZERO

        # A payout 5 triggers the selected trader-wide live transition after
        # the current event: eligible funded accounts move; all sim accounts close.
        if promotion and not promotion.get("processed"):
            for account in funded:
                if account.status == "active" and account.payout_count >= 1:
                    account.status = "promoted_to_live"
                    live = SimAccount(account.account_id, account.attempt, "live", index + 1)
                    live.balance = ZERO
                    live.live = LiveStage(account.account_id)
                    live.start_day = session_ordinal + 1
                    live.start_session_id = next((sid for sid, ordinal in session_ordinals.items()
                                                   if ordinal == session_ordinal + 1), None)
                    live_accounts.append(live); accounts.append(live)
                    account.live_account_id = live.account_id
                    _record_duration(account, session_ordinal, event.session_id)
            for account in [a for a in funded if a.payout_count == 0]:
                if account is None or account.status != "active":
                    continue
                remaining = account.balance - account.floor
                if remaining >= D("500"):
                    refund = purchase_fee
                    total_spend -= refund
                    cash_ledger.append({"type": "evaluation_fee_refund", "account_id": account.account_id,
                                        "timestamp": event.timestamp.isoformat(), "amount": str(refund),
                                        "reason": "live_transition_and_at_least_half_drawdown_remaining"})
                account.status = "closed_by_live_transition"
                account.terminal_reason = "trader_wide_live_transition"
                _record_duration(account, session_ordinal, event.session_id)
            if pending_activation is not None:
                pending_activation["evaluation"].status = "closed_by_live_transition"
                pending_activation["evaluation"].terminal_reason = "trader_wide_live_transition"
                _record_duration(pending_activation["evaluation"], session_ordinal, event.session_id)
                pending_activation = None
            if active_eval is not None:
                active_eval.status = "closed_by_live_transition"
                active_eval.terminal_reason = "trader_wide_live_transition"
                _record_duration(active_eval, session_ordinal, event.session_id)
                active_eval = None
            promotion["processed"] = True

        if active_eval is not None and active_eval.status in ("passed", "breached"):
            _record_duration(active_eval, session_ordinal, event.session_id)
            duration = active_eval.duration_trading_sessions
            if active_eval.status == "passed":
                evaluation_pass_durations.append(duration)
            else:
                evaluation_breach_durations.append(duration)
            next_eval_after_session = event.session_id
            active_eval = None

    # Data exhaustion leaves active accounts unfinished, never failed.
    for a in accounts:
        if a.stage == "live":
            a.status = a.live.status if a.live else a.status
    resolved_evals = [a for a in accounts if a.stage == "evaluation"]
    # Replace stage on promoted funded records only for presentation; retain
    # original funded account snapshot and separate live-stage record.
    last_day = len(session_ordinals)
    last_session_id = period["last_observed_session"]
    for a in resolved_evals:
        if a.status == "active":
            a.status = "unfinished"
            _record_duration(a, last_day, last_session_id)
    eval_counts = {s: sum(a.status == s for a in resolved_evals)
                   for s in ("passed", "breached", "unfinished", "closed_by_live_transition")}
    for a in funded:
        if a.status == "active":
            a.status = "unfinished"
            _record_duration(a, last_day, last_session_id)
        if a.duration_trading_sessions is not None:
            funded_duration_values.append(a.duration_trading_sessions)
    funded_counts = {s: sum(a.status == s for a in funded)
                     for s in ("active", "unfinished", "breached", "promoted_to_live", "closed_by_live_transition")}
    for account in accounts:
        if account.stage == "live" and account.status == "active":
            account.status = "unfinished"
            _record_duration(account, last_day, last_session_id)
    payout_receipts = sum((D(row["amount"]) for row in cash_ledger
                           if row["type"] in ("funded_payout_receipt", "live_bonus_receipt")), ZERO)
    known_costs = total_spend
    net_cash = payout_receipts - known_costs
    accounts_json = []
    for a in accounts:
        if a.stage == "live":
            snap = a.live.snapshot()
            accounts_json.append({"account_id": a.account_id, "attempt": a.attempt,
                                  "stage": "live", "status": a.status,
                                  "start_session": a.start_session_id,
                                  "end_session": a.end_session_id,
                                  "duration_trading_sessions": a.duration_trading_sessions,
                                  "live_snapshot": snap, "events": a.live.events})
        else:
            accounts_json.append(a.snapshot())
    eval_by_attempt = {a.attempt: a for a in accounts if a.stage == "evaluation"}
    funded_by_attempt = {a.attempt: a for a in funded}
    live_by_attempt = {a.attempt: a for a in live_accounts}
    attempt_summaries = []
    for attempt in range(1, purchase_count + 1):
        evaluation = eval_by_attempt.get(attempt)
        funded_account = funded_by_attempt.get(attempt)
        live_account = live_by_attempt.get(attempt)
        evaluation_profile = _trade_profile(evaluation.events, "trade_applied",
                                            evaluation.duration_trading_sessions) if evaluation else {}
        funded_profile = _trade_profile(funded_account.events, "trade_applied",
                                        funded_account.duration_trading_sessions) if funded_account else {}
        live_profile = _trade_profile(live_account.live.events, "live_trade_applied",
                                      live_account.duration_trading_sessions) if live_account else {}
        payouts = funded_account.payouts if funded_account else []
        live_bonus = sum((D(event.get("trader_receipt", "0")) for event in live_account.live.events
                          if event.get("type") == "live_bonus_paid"), ZERO) if live_account else ZERO
        attempt_summaries.append({
            "attempt": attempt,
            "evaluation_status": evaluation.status if evaluation else "not_started",
            "evaluation_start_session": evaluation.start_session_id if evaluation else None,
            "evaluation_end_session": evaluation.end_session_id if evaluation else None,
            "evaluation_duration_sessions": evaluation.duration_trading_sessions if evaluation else None,
            "evaluation_profit": str(evaluation.applied_net) if evaluation else None,
            "evaluation_trade_count": evaluation.trade_count if evaluation else 0,
            "evaluation_cont_trades": evaluation_profile.get("continuation_trades", 0),
            "evaluation_rev_trades": evaluation_profile.get("reversal_trades", 0),
            "evaluation_other_signal_trades": evaluation_profile.get("other_signal_trades", 0),
            "evaluation_trading_days_with_trades": evaluation_profile.get("trading_days_with_trades", 0),
            "evaluation_stage_trading_days": evaluation_profile.get("stage_trading_days", 0),
            "evaluation_trades_per_day": evaluation_profile.get("trades_per_trading_day", "0.00"),
            "evaluation_win_rate": evaluation_profile.get("win_rate", "N/A"),
            "evaluation_reward_risk": evaluation_profile.get("realized_reward_risk"),
            "funded_status": funded_account.status if funded_account else "not_funded",
            "funded_start_session": funded_account.start_session_id if funded_account else None,
            "funded_end_session": funded_account.end_session_id if funded_account else None,
            "funded_duration_sessions": funded_account.duration_trading_sessions if funded_account else None,
            "funded_profit": str(funded_account.applied_net) if funded_account else None,
            "funded_trade_count": funded_account.trade_count if funded_account else 0,
            "funded_cont_trades": funded_profile.get("continuation_trades", 0),
            "funded_rev_trades": funded_profile.get("reversal_trades", 0),
            "funded_other_signal_trades": funded_profile.get("other_signal_trades", 0),
            "funded_trading_days_with_trades": funded_profile.get("trading_days_with_trades", 0),
            "funded_stage_trading_days": funded_profile.get("stage_trading_days", 0),
            "funded_trades_per_day": funded_profile.get("trades_per_trading_day", "0.00"),
            "funded_win_rate": funded_profile.get("win_rate", "N/A"),
            "funded_reward_risk": funded_profile.get("realized_reward_risk"),
            "payout_count": funded_account.payout_count if funded_account else 0,
            "payout_gross": str(sum((D(p["gross_request"]) for p in payouts), ZERO)),
            "payout_receipts": str(sum((D(p["trader_receipt"]) for p in payouts), ZERO)),
            "live_status": live_account.status if live_account else "not_started",
            "live_start_session": live_account.start_session_id if live_account else None,
            "live_end_session": live_account.end_session_id if live_account else None,
            "live_duration_sessions": live_account.duration_trading_sessions if live_account else None,
            "live_profit": live_profile.get("net_pnl"),
            "live_trade_count": live_profile.get("trade_count", 0),
            "live_cont_trades": live_profile.get("continuation_trades", 0),
            "live_rev_trades": live_profile.get("reversal_trades", 0),
            "live_other_signal_trades": live_profile.get("other_signal_trades", 0),
            "live_trading_days_with_trades": live_profile.get("trading_days_with_trades", 0),
            "live_stage_trading_days": live_profile.get("stage_trading_days", 0),
            "live_trades_per_day": live_profile.get("trades_per_trading_day", "0.00"),
            "live_win_rate": live_profile.get("win_rate", "N/A"),
            "live_reward_risk": live_profile.get("realized_reward_risk"),
            "live_bonus_receipts": str(live_bonus),
            "final_status": (live_account.status if live_account else
                             funded_account.status if funded_account else
                             evaluation.status if evaluation else "not_started")})
    total_trades = trade_stats["wins"] + trade_stats["losses"] + trade_stats["breakevens"]
    session_summary = []
    for session in sorted(source_sessions):
        row = source_sessions[session]
        session_summary.append({key: str(value) if isinstance(value, Decimal) else value
                                for key, value in row.items()})
    avg_win = trade_stats["winning_net"] / trade_stats["wins"] if trade_stats["wins"] else None
    avg_loss = trade_stats["losing_net"] / trade_stats["losses"] if trade_stats["losses"] else None
    funded_gross = sum((D(payout["gross_request"]) for a in funded for payout in a.payouts), ZERO)
    funded_receipts = sum((D(payout["trader_receipt"]) for a in funded for payout in a.payouts), ZERO)
    bonus_receipts = sum((D(row["amount"]) for row in cash_ledger if row["type"] == "live_bonus_receipt"), ZERO)
    ledger_net = sum((D(row["amount"]) for row in cash_ledger), ZERO)
    if ledger_net != net_cash:
        raise ValueError(f"Cash ledger does not reconcile: {ledger_net} != {net_cash}")
    scorecard = [
        ["Backtest", f"{period['observed_session_count']} days, {total_trades} trades ({period['first_observed_session']}–{period['last_observed_session']})"],
        ["Win rate", f"{_percent(trade_stats['wins'], total_trades)} ({trade_stats['wins']} / {total_trades})"],
        ["Win / loss", f"+${avg_win.quantize(D('0.01')) if avg_win is not None else 'N/A'} / -${abs(avg_loss).quantize(D('0.01')) if avg_loss is not None else 'N/A'}"],
        ["RR", f"{(avg_win / abs(avg_loss)).quantize(D('0.01')) if avg_win is not None and avg_loss else 'N/A'}"],
        ["Evaluations purchased", f"{purchase_count} / {max_attempts}"],
        ["Eval pass rate", f"{eval_counts['passed']} / {purchase_count} ({_percent(eval_counts['passed'], purchase_count)})"],
        ["Eval breach rate", f"{eval_counts['breached']} / {purchase_count} ({_percent(eval_counts['breached'], purchase_count)})"],
        ["Eval unfinished / closed", f"{eval_counts['unfinished'] + eval_counts['closed_by_live_transition']}"],
        ["Funded accounts", f"{len(funded)} activated; {funded_counts['promoted_to_live']} moved live"],
        ["Funded per 15 evaluations", f"{D(len(funded)) / purchase_count * D('15'):.1f} observed ratio" if purchase_count else "N/A"],
        ["Funded payouts", f"{sum(a.payout_count for a in funded)} gross ${funded_gross.quantize(D('0.01'))}; receipts ${funded_receipts.quantize(D('0.01'))}"],
        ["At least 1 payout", f"{sum(a.payout_count > 0 for a in funded)} / {len(funded)}"],
        ["Payout 5 / live", f"{sum(a.payout_count >= 5 for a in funded)} reached payout 5; {len(live_accounts)} live accounts"],
        ["Payout milestones", f"≥2 payouts: {sum(a.payout_count >= 2 for a in funded)}; ≥3: {sum(a.payout_count >= 3 for a in funded)}"],
        ["Live bonus receipts", f"${bonus_receipts.quantize(D('0.01'))}"],
        ["Ordinary live payouts", "Unmodeled; payout amount/cap not stated in source"],
        ["Evaluation fees", f"${known_costs.quantize(D('0.01'))} net of modeled refunds"],
        ["Net cash profit", f"{'-' if net_cash < ZERO else ''}${abs(net_cash).quantize(D('0.01'))} before unverified external fees"],
        ["Evaluation time to pass", _duration_summary(evaluation_pass_durations)],
        ["Evaluation time to breach", _duration_summary(evaluation_breach_durations)],
        ["Funded time to first payout", _duration_summary(first_payout_durations)],
        ["Funded time in stage", _duration_summary(funded_duration_values)],
    ]
    return {"status": "passed", "scenario": "LucidFlex 25K DLL ON / 50% consistency",
            "strategy": {"name": source.metadata.get("strategy_name", "Unknown strategy"),
                "project_name": "FairPriceStrategy / Cont & Rev",
                "description": "NY-open fair-price strategy: opening-direction continuation, then reversion toward the 9:30 fair-price anchor.",
                "instrument": source.metadata.get("instrument"),
                "bars_period": source.metadata.get("bars_period"),
                "trading_hours_template": source.metadata.get("trading_hours_template"),
                "trading_hours_timezone": source.metadata.get("trading_hours_timezone"),
                "parameters": source.metadata.get("strategy_parameters", {}),
                "runtime_settings": source.metadata.get("runtime_settings", {}),
                "source_commission_mode": source.metadata.get("commission_mode", "unknown"),
                "simulated_size": "1 MNQ per active account; not quantity-scaled"},
            "input_run_id": source.metadata["run_id"], "selected_period": period,
            "requested_attempts": max_attempts, "purchased_attempts": purchase_count,
            "evaluation_outcomes": eval_counts, "funded_outcomes": funded_counts,
            "source_trade_statistics": {"trades": total_trades, "wins": trade_stats["wins"],
                "losses": trade_stats["losses"], "breakevens": trade_stats["breakevens"],
                "win_rate": _percent(trade_stats["wins"], total_trades),
                "average_win": str(avg_win) if avg_win is not None else None,
                "average_loss": str(avg_loss) if avg_loss is not None else None,
                "realized_reward_risk": str((avg_win / abs(avg_loss)).quantize(D("0.01"))) if avg_win is not None and avg_loss else None},
            "payout_receipts": str(payout_receipts), "funded_gross_payout_requests": str(funded_gross),
            "funded_payout_receipts": str(funded_receipts), "live_bonus_receipts": str(bonus_receipts),
            "known_external_costs_net_of_refunds": str(known_costs), "net_cash_profit_before_unverified_fees": str(net_cash),
            "cash_ledger_reconciliation": {"ledger_net": str(ledger_net), "status": "passed"},
            "source_session_summary": session_summary,
            "promotion": promotion, "scorecard": scorecard, "accounts": accounts_json,
            "attempt_summaries": attempt_summaries,
            "cash_ledger": cash_ledger,
            "validation": source.validation, "legacy_replay_result": source.legacy_result,
            "input_hashes": list(source.input_hashes),
            "model_code_hashes": [{"path": str((SIMULATOR / filename).resolve()),
                                   "sha256": _sha256(SIMULATOR / filename)}
                                  for filename in ("lifecycle_study.py", "live_stage.py",
                                                   "account_adapter.py", "account_engine.py",
                                                   "study_period.py")],
            "rule_sources": {
                "payouts": "https://support.lucidtrading.com/en/articles/12945796-lucidflex-payouts",
                "drawdown": "https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown",
                "consistency": "https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage",
                "DLL": "https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization",
                "funded_scaling": "https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan",
                "live": "https://support.lucidtrading.com/en/articles/16558826-new-live-structure"},
            "policies": {"purchase_fee": str(purchase_fee), "funded_start": "fresh $25,000",
                "evaluation_consistency": "strict 50%; published cushion intentionally not used",
                "dll": "$600 soft lock until next observed session; applied throughout funded phase (above-trail behavior unknown)",
                "payout": "minimum $500; min(50% cycle net, $1,000); request only when amount <= current-session profit since prior payout; zero delay policy",
                "payout_floor": "lock $25,100 before gross deduction; breach on equality",
                "live_trigger": "first account payout 5 triggers trader-wide move; selected deterministic simplification",
                "live": "new $0 account per eligible funded account; first $1,000 bonus objective tracked; ordinary live payouts unmodeled"},
            "limitations": ["DLL above the initial trail is unresolved; modeled as $600 throughout funded stage.",
                "Evaluation consistency uses strict 50%; published cushion is omitted, which may reduce passes.",
                "Qualifying-day basis is modeled using completed-trade net daily P&L >= $100.",
                "Payout amount/floor sequence and immediate settlement are user-selected study assumptions.",
                "Unknown payout/payment and external costs are not established as zero; net is before unverified fees.",
                "Payout 5 promotion is modeled as immediate/trader-wide although actual risk-team transition is discretionary.",
                "Ordinary live payouts and bonus cycles after the first are unmodeled.",
                "Completed-trade model excludes intratrade loss-limit touches; final unobserved session is not force-closed.",
                "This is one chronological historical replay; no repeated-cycle probability estimates are implied."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=PROJECT / "logs/logging-on/0.1")
    parser.add_argument("--analyzer-trades", type=Path)
    parser.add_argument("--analyzer-summary", type=Path)
    parser.add_argument("--validation-config", type=Path,
                        default=SIMULATOR / "configs/lucidflex_25k_provisional.json")
    parser.add_argument("--max-attempts", type=int, default=50)
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    args.analyzer_trades = args.analyzer_trades or args.run / "analyzer-trades.csv"
    args.analyzer_summary = args.analyzer_summary or args.run / "analyzer-summary.csv"
    config = load_config(args.validation_config.resolve())
    output = args.out or PROJECT / "simulation-results/lifecycle-study/latest"
    output.mkdir(parents=True, exist_ok=args.out is None)
    try:
        source = load_account_input(args.run, args.analyzer_trades, args.analyzer_summary,
                                    config, config["commission_per_contract_per_side"])
        selected, period = select_period(source.events, args.start_date, args.end_date)
        result = run_lifecycle(source, selected, period, args.max_attempts, D("43.20"))
        dump(output / "lifecycle-study.json", result)
        session_fields = ("session_id", "trade_count", "wins", "losses", "breakevens",
                          "gross_pnl", "commissions", "net_pnl")
        with (output / "session-summary.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=session_fields)
            writer.writeheader()
            writer.writerows(result["source_session_summary"])
        with (output / "account-lifecycle.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(result["attempt_summaries"][0])
                                    if result["attempt_summaries"] else ["attempt"])
            writer.writeheader()
            writer.writerows(result["attempt_summaries"])
        table = ["# 50-purchase lifecycle study", "", "| Stat | Value |", "|---|---|"]
        table.extend(f"| {row[0]} | {row[1]} |" for row in result["scorecard"])
        strategy = result["strategy"]
        table += ["", "## Strategy and source run", "",
                  f"- Strategy: {strategy['name']} ({strategy['project_name']})",
                  f"- Description: {strategy['description']}",
                  f"- Source: {strategy['instrument']}, {strategy['bars_period']}, {strategy['trading_hours_template']}",
                  f"- Simulated sizing: {strategy['simulated_size']}",
                  f"- Run ID: `{result['input_run_id']}`",
                  "- Full parameter and runtime settings are retained in `lifecycle-study.json` and `dashboard.html`."]
        table += ["", "## Account-by-account results", "",
                  "Each attempt joins its evaluation, funded, and live stages. Session ranges and durations use observed trading sessions.",
                  "", "| Attempt | Eval | Eval period | Eval P&L | Eval trades (CONT/REV; per day) | Eval WR / RR | Funded | Funded trades (CONT/REV; per day) | Payouts | Live | Live trades (CONT/REV; per day) | Live WR / RR |",
                  "|---:|---|---|---:|---|---|---|---|---:|---|---|---|"]
        for row in result["attempt_summaries"]:
            eval_period = f"{row['evaluation_start_session'] or '—'}–{row['evaluation_end_session'] or '—'} ({row['evaluation_duration_sessions'] if row['evaluation_duration_sessions'] is not None else '—'} sessions)"
            eval_trades = f"{row['evaluation_trade_count']} ({row['evaluation_cont_trades']}/{row['evaluation_rev_trades']}; {row['evaluation_trades_per_day']}/day over {row['evaluation_stage_trading_days']} days)"
            funded_trades = f"{row['funded_trade_count']} ({row['funded_cont_trades']}/{row['funded_rev_trades']}; {row['funded_trades_per_day']}/day over {row['funded_stage_trading_days']} days)"
            live_trades = f"{row['live_trade_count']} ({row['live_cont_trades']}/{row['live_rev_trades']}; {row['live_trades_per_day']}/day over {row['live_stage_trading_days']} days)"
            table.append(f"| {row['attempt']} | {row['evaluation_status']} | {eval_period} | ${row['evaluation_profit'] or '—'} | {eval_trades} | {row['evaluation_win_rate']} / {row['evaluation_reward_risk'] or 'N/A'} | {row['funded_status']} | {funded_trades} | {row['payout_count']} (${row['payout_receipts']}) | {row['live_status']} | {live_trades} | {row['live_win_rate']} / {row['live_reward_risk'] or 'N/A'} |")
        table += ["", "## Model notes", ""]
        table += [f"- {note}" for note in result["limitations"]]
        table += ["", "CONT/REV count entry signal prefixes. Per-day averages divide stage trades by all observed trading sessions in that stage, including no-trade sessions. `account-lifecycle.csv` also gives sessions with trades and separately counts other signal prefixes. Detailed stage metrics and event traces are in `account-lifecycle.csv` and `lifecycle-study.json`; source-level daily counts and P&L are in `session-summary.csv`."]
        (output / "report.md").write_text("\n".join(table) + "\n", encoding="utf-8")
        write_dashboard(result, output)
        print(json.dumps({"status": "passed", "purchased_attempts": result["purchased_attempts"],
                          "evaluation_outcomes": result["evaluation_outcomes"],
                          "funded_outcomes": result["funded_outcomes"],
                          "net_cash_profit_before_unverified_fees": result["net_cash_profit_before_unverified_fees"],
                          "output": str(output.resolve())}))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        dump(output / "lifecycle-study.json", {"status": "failed", "error": str(exc)})
        print(f"Lifecycle study failed: {exc}\nReport: {output}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
