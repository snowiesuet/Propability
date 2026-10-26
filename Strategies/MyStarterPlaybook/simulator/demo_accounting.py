"""Print the accounting checkpoint using synthetic trades, without writing files."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from account_engine import AccountLedger, CompletedTrade


def main() -> None:
    ledger = AccountLedger("demo-account", Decimal("25000"))
    start = datetime(2026, 1, 2, 15, tzinfo=timezone.utc)
    print("ACCOUNTING DEMO - synthetic trades, not historical strategy results")
    print("Starting balance: $25,000.00\n")
    print(f"{'Trade':<8}{'Gross P&L':>13}{'Commission':>13}{'Net P&L':>13}{'Balance':>15}")
    print("-" * 62)
    trades = []
    for index, gross in enumerate(("101", "-49", "1", "151"), 1):
        trade = CompletedTrade(
            trade_id=f"demo-{index}",
            entry_timestamp=start + timedelta(minutes=index * 2),
            exit_timestamp=start + timedelta(minutes=index * 2 + 1),
            session_id="demo-session", source_order=index, quantity=1,
            gross_pnl=Decimal(gross), commission=Decimal("1"),
        )
        trades.append(trade)
        event, = ledger.apply_trade(trade)
        print(f"{index:<8}{event.gross_pnl:>13,.2f}{event.commission:>13,.2f}"
              f"{event.net_pnl:>13,.2f}{event.balance_after:>15,.2f}")

    result = ledger.snapshot()
    print(f"\nNet profit: ${Decimal(result['net_pnl']):,.2f}")
    print(f"Total commissions: ${Decimal(result['commissions']):,.2f}")
    print(f"Wins / losses / breakevens: {result['wins']} / {result['losses']} / {result['breakevens']}")
    print(f"Win rate: {Decimal(result['win_rate']):.0%}")
    print(f"Average win / loss: ${Decimal(result['average_win']):,.2f} / "
          f"${Decimal(result['average_loss']):,.2f}")
    print(f"Maximum closed-trade drawdown: ${Decimal(result['max_closed_trade_drawdown']):,.2f}")
    print("Hand-calculated reference: $25,200.00 ending balance; $50.00 maximum drawdown.")

    before = ledger.snapshot()
    try:
        ledger.apply_trade(trades[-1])
    except ValueError as error:
        print(f"\nDuplicate trade rejected: {error}")
        print(f"Account unchanged: {ledger.snapshot() == before}")
    else:
        raise RuntimeError("Demo failed: duplicate trade was accepted")
    print("\nThis demo covers accounting. See demo_loss_limits.py and demo_session_rules.py for account rules.")


if __name__ == "__main__":
    main()
