"""Show increment 2 with synthetic trades; writes no data or result files."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from account_engine import AccountEngine, AccountRules, CompletedTrade, SessionClose


START = datetime(2026, 1, 2, 15, tzinfo=timezone.utc)


def sample(order: int, gross: str, session: str) -> CompletedTrade:
    return CompletedTrade(f"trade-{order}", START + timedelta(minutes=2 * order),
                          START + timedelta(minutes=2 * order + 1), session,
                          order, 1, D(gross), D("1"))


def show(engine: AccountEngine, label: str, events: tuple[dict, ...]) -> None:
    state = engine.snapshot()
    print(f"{label:<32} ${D(state['balance']):>10,.2f}  "
          f"{state['status']:<9} DLL lock: {str(state['dll_locked']):<5}  "
          f"{', '.join(event['type'] for event in events)}")


def main() -> None:
    print("LOSS-LIMIT DEMO - synthetic trades, fixed-floor development model")
    print("Start $25,000; fixed loss floor $24,000; net-session DLL $600.")
    print("Each applied trade pays $1 commission. Skipped/ignored trades pay nothing.\n")
    rules = AccountRules(D("25000"), D("24000"), D("600"))
    engine = AccountEngine("dll-demo", rules)
    show(engine, "Day 1: net -$600", engine.apply_trade(sample(1, "-599", "day-1")))
    show(engine, "Day 1: +$500 trade skipped", engine.apply_trade(sample(2, "501", "day-1")))
    show(engine, "Day 1: observed session close", engine.close_session(
        SessionClose("day-1", START + timedelta(minutes=7), 3)))
    show(engine, "Day 2: net +$100", engine.apply_trade(sample(4, "101", "day-2")))
    print("Expected: $24,500 balance, active, DLL unlocked; $2 total commissions.")

    print("\nSeparate account: hard breach takes priority over DLL.")
    breached = AccountEngine("breach-demo", rules)
    show(breached, "Day 1: net -$1,000", breached.apply_trade(sample(1, "-999", "day-1")))
    show(breached, "Later +$5,000 trade ignored", breached.apply_trade(sample(2, "5001", "day-1")))
    print("Expected: $24,000 balance, breached; $1 total commissions.")
    print("\nFor trailing/evaluation examples, run demo_session_rules.py. Historical ingestion and payouts are pending.")


if __name__ == "__main__":
    main()
