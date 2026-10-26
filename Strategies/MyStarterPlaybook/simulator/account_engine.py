"""Completed-trade account building blocks, independent of legacy replay.

The engine supports explicit fixed/EOD trailing floors, net-session DLL,
evaluation target/strict consistency, and funded qualifying-day accounting.
These development policies are not a provider rulebook or payout engine.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


ZERO = Decimal("0")


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _money(value: Decimal, name: str) -> None:
    # Require explicit Decimal conversion at the input boundary; floats can
    # silently carry binary rounding errors into financial arithmetic.
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")


def _timestamp(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _instant(value: datetime) -> datetime:
    # UTC comparison also handles a repeated wall-clock hour at DST fallback.
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class CompletedTrade:
    """One flat-to-flat, one-contract trade; P&L fields are increments.

    Session IDs are supplied by the caller. This ledger does not derive exchange
    sessions from calendar dates. The future validated-run adapter must prove
    flat-to-flat inventory; quantity alone cannot establish that property.
    """

    trade_id: str
    entry_timestamp: datetime
    exit_timestamp: datetime
    session_id: str
    source_order: int
    quantity: int
    gross_pnl: Decimal
    commission: Decimal

    def __post_init__(self) -> None:
        _identifier(self.trade_id, "trade_id")
        _identifier(self.session_id, "session_id")
        _timestamp(self.entry_timestamp, "entry_timestamp")
        _timestamp(self.exit_timestamp, "exit_timestamp")
        if _instant(self.entry_timestamp) > _instant(self.exit_timestamp):
            raise ValueError("entry_timestamp must not follow exit_timestamp")
        if type(self.source_order) is not int or self.source_order < 0:
            raise ValueError("source_order must be a nonnegative integer")
        if type(self.quantity) is not int or self.quantity != 1:
            raise ValueError("only one-contract completed trades are supported")
        _money(self.gross_pnl, "gross_pnl")
        _money(self.commission, "commission")
        if self.commission < ZERO:
            raise ValueError("commission must not be negative")

    @property
    def net_pnl(self) -> Decimal:
        return self.gross_pnl - self.commission


@dataclass(frozen=True)
class TradeApplied:
    account_id: str
    trade_id: str
    session_id: str
    gross_pnl: Decimal
    commission: Decimal
    net_pnl: Decimal
    balance_before: Decimal
    balance_after: Decimal


class AccountLedger:
    """Per-account accounting only; all trades supplied are included.

    AccountEngine decides which trades are eligible before applying them here.
    Invalid input leaves ledger state unchanged. No global trade-ID
    registry or source cumulative balance is shared between accounts.
    """

    def __init__(self, account_id: str, starting_capital: Decimal):
        _identifier(account_id, "account_id")
        _money(starting_capital, "starting_capital")
        if starting_capital <= ZERO:
            raise ValueError("starting_capital must be positive")
        self._account_id = account_id
        self._starting_capital = starting_capital
        self._balance = starting_capital
        self._gross = self._commissions = ZERO
        self._peak = starting_capital
        self._max_drawdown = ZERO
        self._wins = self._losses = self._breakevens = 0
        self._winning_pnl = self._losing_pnl = ZERO
        self._seen: set[str] = set()
        self._last_trade: CompletedTrade | None = None
        self._session_pnl: dict[str, Decimal] = {}

    def apply_trade(self, trade: CompletedTrade) -> tuple[TradeApplied, ...]:
        if not isinstance(trade, CompletedTrade):
            raise ValueError("trade must be a CompletedTrade")
        if trade.trade_id in self._seen:
            raise ValueError(f"duplicate trade_id: {trade.trade_id}")
        previous = self._last_trade
        if previous is not None:
            if (_instant(trade.exit_timestamp), trade.source_order) <= (
                _instant(previous.exit_timestamp), previous.source_order
            ):
                raise ValueError("trade input must follow timestamp/source order")
            if trade.source_order <= previous.source_order:
                raise ValueError("source_order must strictly increase")
            if _instant(trade.entry_timestamp) < _instant(previous.exit_timestamp):
                raise ValueError("overlapping trades are unsupported")

        net = trade.net_pnl
        before = self._balance
        self._balance += net
        self._gross += trade.gross_pnl
        self._commissions += trade.commission
        self._peak = max(self._peak, self._balance)
        self._max_drawdown = max(self._max_drawdown, self._peak - self._balance)
        self._session_pnl[trade.session_id] = self._session_pnl.get(trade.session_id, ZERO) + net
        if net > ZERO:
            self._wins += 1
            self._winning_pnl += net
        elif net < ZERO:
            self._losses += 1
            self._losing_pnl += net
        else:
            self._breakevens += 1
        self._seen.add(trade.trade_id)
        self._last_trade = trade
        return (TradeApplied(self._account_id, trade.trade_id, trade.session_id,
                             trade.gross_pnl, trade.commission, net, before, self._balance),)

    def snapshot(self) -> dict:
        """Detached JSON-serializable accounting, with undefined ratios as None."""
        count = len(self._seen)
        average_win = self._winning_pnl / self._wins if self._wins else None
        average_loss = self._losing_pnl / self._losses if self._losses else None
        return {
            "account_id": self._account_id,
            "starting_capital": str(self._starting_capital),
            "balance": str(self._balance),
            "gross_pnl": str(self._gross),
            "commissions": str(self._commissions),
            "net_pnl": str(self._gross - self._commissions),
            "trade_count": count,
            "wins": self._wins,
            "losses": self._losses,
            "breakevens": self._breakevens,
            "win_rate": str(Decimal(self._wins) / count) if count else None,
            "average_win": str(average_win) if average_win is not None else None,
            "average_loss": str(average_loss) if average_loss is not None else None,
            "realized_reward_risk": str(average_win / abs(average_loss))
                if average_win is not None and average_loss is not None else None,
            "peak_balance": str(self._peak),
            "max_closed_trade_drawdown": str(self._max_drawdown),
            "session_net_pnl": {key: str(value) for key, value in self._session_pnl.items()},
        }


@dataclass(frozen=True)
class AccountRules:
    """Explicit development policies; no unresolved provider rule is inferred.

    The default development account preserves the increment-2 fixed-floor API.
    Evaluation/funded accounts require their stage-specific settings explicitly.
    EOD trailing uses max(old floor, min(cap, highest closed balance - distance)).
    """

    starting_capital: Decimal
    loss_floor: Decimal
    daily_loss_limit: Decimal | None
    account_type: str = "development"
    loss_model: str = "fixed"
    trailing_distance: Decimal | None = None
    floor_cap: Decimal | None = None
    evaluation_target: Decimal | None = None
    consistency_limit: Decimal | None = None
    consistency_policy: str | None = None
    qualifying_day_profit: Decimal | None = None

    def __post_init__(self) -> None:
        _money(self.starting_capital, "starting_capital")
        _money(self.loss_floor, "loss_floor")
        if self.starting_capital <= ZERO:
            raise ValueError("starting_capital must be positive")
        if not ZERO <= self.loss_floor < self.starting_capital:
            raise ValueError("loss_floor must be nonnegative and below starting_capital")
        if self.daily_loss_limit is not None:
            _money(self.daily_loss_limit, "daily_loss_limit")
            if self.daily_loss_limit <= ZERO:
                raise ValueError("daily_loss_limit must be positive or None")
        if self.account_type not in ("development", "evaluation", "funded"):
            raise ValueError("unsupported account_type")
        if self.loss_model == "eod_trailing":
            _money(self.trailing_distance, "trailing_distance")
            _money(self.floor_cap, "floor_cap")
            if self.trailing_distance <= ZERO:
                raise ValueError("trailing_distance must be positive")
            if self.loss_floor != self.starting_capital - self.trailing_distance:
                raise ValueError("initial loss_floor must equal starting_capital minus trailing_distance")
            if self.floor_cap < self.loss_floor:
                raise ValueError("floor_cap must not be below initial loss_floor")
        elif self.loss_model != "fixed":
            raise ValueError("unsupported loss_model")
        elif self.trailing_distance is not None or self.floor_cap is not None:
            raise ValueError("fixed floor rejects trailing settings")
        if self.account_type == "evaluation":
            _money(self.evaluation_target, "evaluation_target")
            _money(self.consistency_limit, "consistency_limit")
            if self.evaluation_target <= ZERO:
                raise ValueError("evaluation_target must be positive")
            if not ZERO < self.consistency_limit <= Decimal("1"):
                raise ValueError("consistency_limit must be in (0, 1]")
            if self.consistency_policy != "strict":
                raise ValueError("evaluation requires explicit strict consistency_policy")
        elif any(value is not None for value in (
                self.evaluation_target, self.consistency_limit, self.consistency_policy)):
            raise ValueError("only evaluation accounts accept target/consistency settings")
        if self.qualifying_day_profit is not None:
            _money(self.qualifying_day_profit, "qualifying_day_profit")
            if self.qualifying_day_profit <= ZERO:
                raise ValueError("qualifying_day_profit must be positive")
        if self.account_type == "funded" and self.qualifying_day_profit is None:
            raise ValueError("funded accounts require qualifying_day_profit")


@dataclass(frozen=True)
class SessionClose:
    session_id: str
    timestamp: datetime
    source_order: int

    def __post_init__(self) -> None:
        _identifier(self.session_id, "session_id")
        _timestamp(self.timestamp, "timestamp")
        if type(self.source_order) is not int or self.source_order < 0:
            raise ValueError("source_order must be a nonnegative integer")


class AccountEngine:
    """Completed-trade account state machine, independent per account.

    Caller-supplied session IDs and explicit close events establish boundaries;
    midnight never resets the DLL. All input, including skipped/terminal input,
    must remain unique and chronologically ordered. Returned audit events are
    detached JSON-serializable dictionaries, not retained mutable engine state.
    """

    def __init__(self, account_id: str, rules: AccountRules):
        if not isinstance(rules, AccountRules):
            raise ValueError("rules must be AccountRules")
        self._ledger = AccountLedger(account_id, rules.starting_capital)
        self._account_id = account_id
        self._rules = rules
        self._status = "active"
        self._dll_locked = False
        self._session_id: str | None = None
        self._session_net = ZERO
        self._completed_sessions = 0
        self._skipped_trades = 0
        self._closed_sessions: set[str] = set()
        self._seen_trades: set[str] = set()
        self._last_timestamp: datetime | None = None
        self._last_order: int | None = None
        self._loss_floor = rules.loss_floor
        self._highest_completed_balance = rules.starting_capital
        self._best_winning_day = ZERO
        self._qualifying_days = 0
        self._data_finished = False

    def _check_open_data(self) -> None:
        if self._data_finished:
            raise ValueError("data already finished; create a new account to replay again")

    def _check_order(self, timestamp: datetime, source_order: int) -> None:
        if self._last_timestamp is not None:
            if _instant(timestamp) < _instant(self._last_timestamp):
                raise ValueError("input timestamps must not go backwards")
            if source_order <= self._last_order:
                raise ValueError("source_order must strictly increase across trades and closes")

    def _check_session(self, session_id: str) -> None:
        if session_id in self._closed_sessions:
            raise ValueError("session is already closed")
        if (self._session_id is not None and self._session_id != session_id
                and self._session_id not in self._closed_sessions):
            raise ValueError("close the current session before starting another")

    def _begin_session(self, session_id: str) -> list[dict]:
        if self._session_id == session_id:
            return []
        self._session_id = session_id
        self._session_net = ZERO
        self._dll_locked = False
        return [{"type": "session_started", "session_id": session_id}]

    def apply_trade(self, trade: CompletedTrade) -> tuple[dict, ...]:
        self._check_open_data()
        if not isinstance(trade, CompletedTrade):
            raise ValueError("trade must be a CompletedTrade")
        if trade.trade_id in self._seen_trades:
            raise ValueError(f"duplicate trade_id: {trade.trade_id}")
        if trade.session_id in self._closed_sessions:
            raise ValueError("session is already closed")
        self._check_order(trade.exit_timestamp, trade.source_order)
        if (self._last_timestamp is not None
                and _instant(trade.entry_timestamp) < _instant(self._last_timestamp)):
            raise ValueError("trade overlaps a preceding trade or session close")
        # A terminal account still validates stream order and uniqueness, but
        # does not require session transitions or change account state.
        if self._status == "active":
            self._check_session(trade.session_id)

        if self._status != "active":
            events = [{"type": "trade_ignored", "trade_id": trade.trade_id,
                       "reason": self._status}]
        else:
            events = self._begin_session(trade.session_id)
            if self._dll_locked:
                self._skipped_trades += 1
                events.append({"type": "trade_skipped", "trade_id": trade.trade_id,
                               "reason": "daily_loss_limit", "session_id": trade.session_id})
            else:
                applied, = self._ledger.apply_trade(trade)
                self._session_net += applied.net_pnl
                events.append({"type": "trade_applied", "trade_id": trade.trade_id,
                               "session_id": trade.session_id, "gross_pnl": str(applied.gross_pnl),
                               "commission": str(applied.commission), "net_pnl": str(applied.net_pnl),
                               "balance_before": str(applied.balance_before),
                               "balance_after": str(applied.balance_after)})
                if applied.balance_after <= self._loss_floor:
                    self._status = "breached"
                    events.append({"type": "account_breached", "trade_id": trade.trade_id,
                                   "balance": str(applied.balance_after),
                                   "loss_floor": str(self._loss_floor)})
                elif (self._rules.daily_loss_limit is not None
                      and self._session_net <= -self._rules.daily_loss_limit):
                    self._dll_locked = True
                    events.append({"type": "dll_locked", "session_id": trade.session_id,
                                   "session_net_pnl": str(self._session_net),
                                   "daily_loss_limit": str(self._rules.daily_loss_limit)})
        self._seen_trades.add(trade.trade_id)
        self._last_timestamp = trade.exit_timestamp
        self._last_order = trade.source_order
        return tuple({"account_id": self._account_id,
                      "timestamp": trade.exit_timestamp.isoformat(),
                      "source_order": trade.source_order, **event} for event in events)

    def close_session(self, event: SessionClose) -> tuple[dict, ...]:
        self._check_open_data()
        if not isinstance(event, SessionClose):
            raise ValueError("event must be a SessionClose")
        self._check_order(event.timestamp, event.source_order)
        if event.session_id in self._closed_sessions:
            raise ValueError("session is already closed")
        if self._status != "active":
            events = [{"type": "session_close_ignored", "session_id": event.session_id,
                       "reason": self._status}]
        else:
            self._check_session(event.session_id)
            events = self._begin_session(event.session_id)
            self._completed_sessions += 1
            balance = Decimal(self._ledger.snapshot()["balance"])
            self._highest_completed_balance = max(self._highest_completed_balance, balance)
            self._best_winning_day = max(self._best_winning_day, self._session_net)
            qualifies = (self._rules.qualifying_day_profit is not None
                         and self._session_net >= self._rules.qualifying_day_profit)
            if qualifies:
                self._qualifying_days += 1
            events.append({"type": "session_closed", "session_id": event.session_id,
                           "session_net_pnl": str(self._session_net),
                           "balance": str(balance), "qualifying_day": qualifies})
            if self._rules.loss_model == "eod_trailing":
                old_floor = self._loss_floor
                self._loss_floor = max(old_floor, min(self._rules.floor_cap,
                    self._highest_completed_balance - self._rules.trailing_distance))
                events.append({"type": "floor_updated", "session_id": event.session_id,
                               "old_floor": str(old_floor), "new_floor": str(self._loss_floor),
                               "triggering_balance": str(balance),
                               "highest_completed_balance": str(self._highest_completed_balance)})
            if balance <= self._loss_floor:
                self._status = "breached"
                events.append({"type": "account_breached", "session_id": event.session_id,
                               "balance": str(balance), "loss_floor": str(self._loss_floor)})
            elif self._rules.account_type == "evaluation":
                profit = balance - self._rules.starting_capital
                target_met = profit >= self._rules.evaluation_target
                # Compare products instead of a rounded ratio at the boundary.
                consistency_met = (profit > ZERO and self._best_winning_day
                                   <= self._rules.consistency_limit * profit)
                if target_met and consistency_met:
                    self._status = "passed"
                events.append({"type": "evaluation_passed" if self._status == "passed"
                               else "evaluation_pending", "session_id": event.session_id,
                               "net_profit": str(profit), "target_met": target_met,
                               "consistency_met": consistency_met,
                               "best_winning_day": str(self._best_winning_day)})
            # Keep lock and closing-day totals until the next observed session.
        self._closed_sessions.add(event.session_id)
        self._last_timestamp = event.timestamp
        self._last_order = event.source_order
        return tuple({"account_id": self._account_id,
                      "timestamp": event.timestamp.isoformat(),
                      "source_order": event.source_order, **item} for item in events)

    def finish_data(self) -> tuple[dict, ...]:
        """Seal input without fabricating a last session close or a failure.

        Active accounts stay active with an unfinished outcome. Repeated calls
        are idempotent. No balance, day count, floor, or terminal status changes.
        """
        if self._data_finished:
            return ()
        self._data_finished = True
        return ({"type": "data_finished", "account_id": self._account_id,
                 "timestamp": self._last_timestamp.isoformat() if self._last_timestamp else None,
                 "source_order": self._last_order,
                 "outcome": "unfinished" if self._status == "active" else self._status},)

    def snapshot(self) -> dict:
        return {
            **self._ledger.snapshot(),
            "account_type": self._rules.account_type,
            "loss_model": self._rules.loss_model,
            "loss_floor": str(self._loss_floor),
            "highest_completed_balance": str(self._highest_completed_balance),
            "best_winning_day": str(self._best_winning_day),
            "qualifying_days": self._qualifying_days,
            "daily_loss_limit": str(self._rules.daily_loss_limit)
                if self._rules.daily_loss_limit is not None else None,
            "status": self._status,
            "dll_locked": self._dll_locked,
            "current_session_id": self._session_id,
            "current_session_net_pnl": str(self._session_net),
            "completed_sessions": self._completed_sessions,
            "skipped_trades": self._skipped_trades,
            "data_finished": self._data_finished,
            "outcome": self._status if self._status != "active"
                else "unfinished" if self._data_finished else None,
        }
