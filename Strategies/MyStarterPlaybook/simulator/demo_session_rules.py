"""Visible increment-3 examples using synthetic completed trades, no file writes."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from account_engine import AccountEngine, AccountRules, CompletedTrade, SessionClose


START = datetime(2026, 1, 2, 15, tzinfo=timezone.utc)


def rules(stage: str) -> AccountRules:
    stage_settings = (dict(evaluation_target=D("1250"), consistency_limit=D("0.5"),
                           consistency_policy="strict") if stage == "evaluation"
                      else dict(qualifying_day_profit=D("100")))
    return AccountRules(D("25000"), D("24000"), D("600"), account_type=stage,
                        loss_model="eod_trailing", trailing_distance=D("1000"),
                        floor_cap=D("25100"), **stage_settings)


def day(engine: AccountEngine, index: int, net: str, close: bool = True) -> None:
    start = START + timedelta(days=index)
    session = f"day-{index + 1}"
    engine.apply_trade(CompletedTrade(f"t-{index}", start, start + timedelta(minutes=1),
                                      session, index * 2 + 1, 1, D(net) + D("1"), D("1")))
    events = engine.close_session(SessionClose(session, start + timedelta(hours=1),
                                               index * 2 + 2)) if close else ()
    state = engine.snapshot()
    decision = next((e for e in events if e["type"].startswith("evaluation_")), None)
    detail = (f"target met: {decision['target_met']}, consistency met: {decision['consistency_met']}"
              if decision else f"qualifying days: {state['qualifying_days']}")
    print(f"{session}: net {D(net):>8,.2f} | balance {D(state['balance']):>10,.2f} | "
          f"floor {D(state['loss_floor']):>10,.2f} | {state['status']:<6} | "
          f"{'closed' if close else 'UNCLOSED'} | {detail}")


def main() -> None:
    print("SESSION-RULE DEMO - synthetic trades, explicit development policies")
    print("$25,000 start; $1,000 EOD trail; $25,100 floor cap; $600 net-session DLL.")
    print("Each net amount includes $1 commission. No historical performance or payouts.\n")
    print("Evaluation: $1,250 target AND strict 50% consistency required at session close.")
    evaluation = AccountEngine("evaluation-demo", rules("evaluation"))
    for index, net in enumerate(("1250", "625", "625")):
        day(evaluation, index, net)
    evaluation.finish_data()
    print(f"Final outcome: {evaluation.snapshot()['outcome']} (best day $1,250 / total profit $2,500).\n")

    print("Funded: each completed net-profit day >= $100 qualifies; no evaluation target.")
    funded = AccountEngine("funded-demo", rules("funded"))
    for index, net in enumerate(("100", "99", "-50", "0", "150")):
        day(funded, index, net)
    funded.finish_data()
    print(f"Final outcome: {funded.snapshot()['outcome']}; two qualifying days, no payout claim.\n")

    print("Missing final session close: meeting the target intraday cannot pass an evaluation.")
    unfinished = AccountEngine("unfinished-demo", rules("evaluation"))
    day(unfinished, 0, "625")
    day(unfinished, 1, "625", close=False)
    unfinished.finish_data()
    print(f"Final outcome: {unfinished.snapshot()['outcome']}; last session was not fabricated.")


if __name__ == "__main__":
    main()
