"""Hand-calculated and synthetic integration fixtures for the lifecycle model."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from account_engine import CompletedTrade, SessionClose
from lifecycle_study import SimAccount, run_lifecycle


START = datetime(2026, 1, 1, 15, tzinfo=timezone.utc)


def day_trade(day, net, source_order):
    entry = START + timedelta(days=day - 1)
    return CompletedTrade(f"trade-{day}", entry, entry + timedelta(minutes=1),
                          entry.date().isoformat(), source_order, 1,
                          D(net) + D("1"), D("1"))


def close_day(day, source_order):
    session = (START + timedelta(days=day - 1)).date().isoformat()
    timestamp = START + timedelta(days=day - 1, hours=1)
    return SessionClose(session, timestamp, source_order)


class LifecycleHandCheckTests(unittest.TestCase):
    def test_funded_first_payout_matches_hand_calculation(self):
        account = SimAccount("funded-01", 1, "funded", 0)
        account.activation_day = 1
        source_order = 1
        for day, net in enumerate(("100", "100", "100", "100", "850"), 1):
            trade = day_trade(day, net, source_order)
            account.apply_trade(trade)
            account.close_session(close_day(day, source_order + 1))
            source_order += 2
        payout = account.payout_if_eligible("2026-01-05", START + timedelta(days=4, hours=1))
        self.assertIsNotNone(payout)
        self.assertEqual(account.qualifying_days, 0)
        self.assertEqual(D(payout["cycle_profit_before_request"]), D("1250"))
        self.assertEqual(D(payout["gross_request"]), D("625"))
        self.assertEqual(D(payout["trader_receipt"]), D("562.50"))
        self.assertEqual(D(payout["balance_before"]), D("26250"))
        self.assertEqual(D(payout["balance_after"]), D("25625"))
        self.assertEqual(D(payout["locked_floor"]), D("25100"))
        self.assertEqual(account.status, "active")

    def test_stops_at_fifty_actual_purchases_without_reusing_trades(self):
        events = []
        for day in range(1, 56):
            source_order = (day - 1) * 2 + 1
            events.append(day_trade(day, "-1000", source_order))
            events.append(close_day(day, source_order + 1))
        sessions = sorted({event.session_id for event in events})
        source = SimpleNamespace(metadata={"run_id": "synthetic-50-cap-fixture"},
                                 validation={"trade_count": 55}, legacy_result={}, input_hashes=())
        period = {"observed_session_count": 55, "first_observed_session": sessions[0],
                  "last_observed_session": sessions[-1], "trade_count": 55}
        result = run_lifecycle(source, tuple(events), period, 50, D("43.20"))
        self.assertEqual(result["purchased_attempts"], 50)
        self.assertEqual(result["evaluation_outcomes"]["breached"], 50)
        self.assertEqual(sum(row["type"] == "evaluation_purchase" for row in result["cash_ledger"]), 50)
        self.assertEqual(D(result["known_external_costs_net_of_refunds"]), D("2160"))
        self.assertEqual(D(result["net_cash_profit_before_unverified_fees"]), D("-2160"))
        self.assertEqual(sum(int(row["trade_count"]) for row in result["source_session_summary"]), 55)
        self.assertTrue(all(a["duration_trading_sessions"] == 1
                            for a in result["accounts"] if a["stage"] == "evaluation"))
        self.assertEqual(result["attempt_summaries"][0]["evaluation_status"], "breached")
        self.assertEqual(result["attempt_summaries"][0]["evaluation_duration_sessions"], 1)
        self.assertEqual(result["attempt_summaries"][0]["funded_status"], "not_funded")
        self.assertIn("mean 1.0", dict(result["scorecard"])["Evaluation time to breach"])

    def test_end_to_end_payout_five_transition_and_live_bonus(self):
        events = []
        source_order = 1
        # A repeatable synthetic path makes payout and live states observable:
        # four +$100 sessions and a +$600 session per cycle. This is a fixture,
        # not historical strategy performance.
        for day in range(1, 71):
            net = "600" if day % 5 == 0 else "100"
            events.append(day_trade(day, net, source_order))
            events.append(close_day(day, source_order + 1))
            source_order += 2
        sessions = sorted({event.session_id for event in events})
        source = SimpleNamespace(metadata={"run_id": "synthetic-lifecycle-fixture"},
                                 validation={"trade_count": 70}, legacy_result={}, input_hashes=())
        period = {"observed_session_count": 70, "first_observed_session": sessions[0],
                  "last_observed_session": sessions[-1], "trade_count": 70}
        result = run_lifecycle(source, tuple(events), period, 50, D("43.20"))

        funded = [a for a in result["accounts"] if a["stage"] == "funded"]
        live = [a for a in result["accounts"] if a["stage"] == "live"]
        evaluations = [a for a in result["accounts"] if a["stage"] == "evaluation"]
        self.assertTrue(any(a["payout_count"] == 5 for a in funded))
        self.assertTrue(live)
        self.assertTrue(all(a["status"] == "promoted_to_live" for a in funded
                            if a["payout_count"] > 0))
        self.assertTrue(any(a["status"] == "closed_by_live_transition" for a in evaluations))
        self.assertTrue(any(a["status"] == "closed_by_live_transition" for a in funded
                            if a["payout_count"] == 0))
        self.assertTrue(any(a["live_snapshot"]["bonus_claimed"] for a in live), live)
        self.assertTrue(any(row["type"] == "live_bonus_receipt" and D(row["amount"]) == D("900")
                            for row in result["cash_ledger"]))
        self.assertTrue(all(isinstance(a["duration_trading_sessions"], int) for a in evaluations))
        self.assertTrue(all(isinstance(a["duration_trading_sessions"], int) for a in live))
        scorecard = dict(result["scorecard"])
        self.assertIn("mean", scorecard["Evaluation time to pass"])
        self.assertIn("mean", scorecard["Funded time in stage"])
        self.assertEqual(D(result["cash_ledger_reconciliation"]["ledger_net"]),
                         D(result["net_cash_profit_before_unverified_fees"]))
        self.assertEqual(sum(int(row["trade_count"]) for row in result["source_session_summary"]), 70)
        self.assertEqual(result["promotion"]["trigger_account_id"],
                         next(a["account_id"] for a in funded if a["payout_count"] == 5))
        first = result["attempt_summaries"][0]
        self.assertEqual(first["evaluation_status"], "passed")
        promoted = next(row for row in result["attempt_summaries"]
                        if row["funded_status"] == "promoted_to_live")
        self.assertIsNotNone(promoted["live_start_session"])
        self.assertGreaterEqual(promoted["payout_count"], 1)
        self.assertIn("%", first["evaluation_win_rate"])
        self.assertTrue(promoted["live_status"] in ("unfinished", "bonus_claimed"))
        self.assertGreaterEqual(D(promoted["live_bonus_receipts"]), D("0"))


if __name__ == "__main__":
    unittest.main()
