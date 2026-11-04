"""LucidLive rules that are explicit in the November 2026 help-center snapshot.

This module tracks a modeled $25K FLEX account after the study's selected
promotion trigger (payout 5). It deliberately does not invent regular live
withdrawal amounts or execution fills.
"""

from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0")


@dataclass(frozen=True)
class LiveRules:
    funded_size: Decimal = Decimal("25000")
    starting_balance: Decimal = ZERO
    starting_drawdown: Decimal = Decimal("1000")
    locked_floor: Decimal = Decimal("-100")
    bonus_profit_target: Decimal = Decimal("2000")
    bonus_trading_days: int = 20
    bonus_gross: Decimal = Decimal("1000")
    trader_split: Decimal = Decimal("0.90")
    max_micro_contracts: int = 20


class LiveStage:
    """Track closed-trade P&L, EOD floor, and first bonus eligibility."""

    def __init__(self, account_id: str, rules: LiveRules = LiveRules()):
        if not account_id:
            raise ValueError("account_id is required")
        self.account_id = account_id
        self.rules = rules
        self.balance = rules.starting_balance
        self.highest_close = rules.starting_balance
        self.floor = rules.starting_balance - rules.starting_drawdown
        self.cumulative_profit = ZERO
        self.bonus_days: set[str] = set()
        self.session_id: str | None = None
        self.session_pnl = ZERO
        self.status = "active"
        self.bonus_eligible = False
        self.bonus_claimed = False
        self.events: list[dict] = []

    def apply_trade(self, session_id: str, net_pnl: Decimal, entry_signal: str | None = None) -> dict:
        if self.status != "active":
            raise ValueError("live account is not active")
        if not isinstance(net_pnl, Decimal) or not net_pnl.is_finite():
            raise ValueError("net_pnl must be a finite Decimal")
        if self.session_id is not None and session_id != self.session_id:
            raise ValueError("close the current session before starting another")
        self.session_id = session_id
        self.balance += net_pnl
        self.session_pnl += net_pnl
        self.cumulative_profit += net_pnl
        if self.balance <= self.floor:
            self.status = "breached"
        event = {"type": "live_trade_applied", "account_id": self.account_id,
                 "session_id": session_id, "net_pnl": str(net_pnl),
                 "entry_signal": entry_signal,
                 "balance": str(self.balance), "floor": str(self.floor),
                 "status": self.status}
        self.events.append(event)
        return event

    def close_session(self, session_id: str) -> dict:
        if self.status != "active":
            raise ValueError("live account is not active")
        if self.session_id != session_id:
            raise ValueError("session_id does not match the active session")
        old_floor = self.floor
        self.highest_close = max(self.highest_close, self.balance)
        # LucidLive MLL trails EOD balance up to the point it locks $100 below
        # the $0 start after $1,000 of generated profit.
        self.floor = max(old_floor, min(self.rules.locked_floor,
                                        self.highest_close - self.rules.starting_drawdown))
        if self.session_pnl >= Decimal("1") or self.session_pnl <= Decimal("-1"):
            self.bonus_days.add(session_id)
        if (self.cumulative_profit >= self.rules.bonus_profit_target
                and len(self.bonus_days) >= self.rules.bonus_trading_days):
            self.bonus_eligible = True
        if self.balance <= self.floor:
            self.status = "breached"
        event = {"type": "live_session_closed", "account_id": self.account_id,
                 "session_id": session_id, "session_net_pnl": str(self.session_pnl),
                 "balance": str(self.balance), "old_floor": str(old_floor),
                 "new_floor": str(self.floor), "highest_close": str(self.highest_close),
                 "bonus_qualifying_days": len(self.bonus_days),
                 "cumulative_live_profit": str(self.cumulative_profit),
                 "bonus_eligible": self.bonus_eligible, "status": self.status}
        self.events.append(event)
        self.session_id = None
        self.session_pnl = ZERO
        return event

    def snapshot(self) -> dict:
        return {"account_id": self.account_id, "stage": "live", "status": self.status,
                "balance": str(self.balance), "highest_eod_balance": str(self.highest_close),
                "loss_floor": str(self.floor), "daily_loss_limit": None,
                "max_micro_contracts": self.rules.max_micro_contracts,
                "live_profit_target": str(self.rules.bonus_profit_target),
                "bonus_trading_days": len(self.bonus_days),
                "bonus_eligible": self.bonus_eligible,
                "bonus_claimed": self.bonus_claimed,
                "bonus_gross_if_claimed": str(self.rules.bonus_gross),
                "bonus_receipt_if_claimed": str(self.rules.bonus_gross * self.rules.trader_split),
                "ordinary_live_payouts": "unmodeled; source does not state request amount/cap"}

    def claim_bonus(self) -> dict:
        if self.status != "active":
            raise ValueError("breached live account cannot claim a bonus")
        if not self.bonus_eligible:
            raise ValueError("live bonus objectives are not complete")
        if self.bonus_claimed:
            raise ValueError("bonus already claimed for this objective cycle")
        self.bonus_claimed = True
        event = {"type": "live_bonus_paid", "account_id": self.account_id,
                 "gross": str(self.rules.bonus_gross),
                 "trader_receipt": str(self.rules.bonus_gross * self.rules.trader_split),
                 "firm_share": str(self.rules.bonus_gross * (Decimal("1") - self.rules.trader_split))}
        self.events.append(event)
        return event
