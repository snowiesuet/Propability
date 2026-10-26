"""Independent, hand-calculated checks for incremental account accounting."""

import json
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from account_engine import AccountEngine, AccountLedger, AccountRules, CompletedTrade, SessionClose


START = datetime(2026, 1, 2, 10, tzinfo=timezone.utc)


def trade(index=1, gross="101", commission="1", session="day-1"):
    return CompletedTrade(str(index), START + timedelta(minutes=2 * index),
                          START + timedelta(minutes=2 * index + 1), session,
                          index, 1, D(gross), D(commission))


class AccountingTests(unittest.TestCase):
    def test_empty_account_and_detached_json_snapshot(self):
        ledger = AccountLedger("a", D("25000"))
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["balance"], "25000")
        self.assertEqual(snapshot["trade_count"], 0)
        for name in ("win_rate", "average_win", "average_loss", "realized_reward_risk"):
            self.assertIsNone(snapshot[name])
        json.dumps(snapshot, allow_nan=False)
        snapshot["session_net_pnl"]["invented"] = "999"
        self.assertEqual(ledger.snapshot()["session_net_pnl"], {})

    def test_hand_calculated_accounting_statistics_and_drawdown(self):
        ledger = AccountLedger("a", D("25000"))
        # Net increments: +100, -50, 0, +150. Peak 25200; worst drawdown 50.
        for index, gross in enumerate(("101", "-49", "1", "151"), 1):
            events = ledger.apply_trade(trade(index, gross))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].balance_after - events[0].balance_before,
                             events[0].net_pnl)
        snapshot = ledger.snapshot()
        for name, expected in {
            "gross_pnl": "204", "commissions": "4", "net_pnl": "200",
            "balance": "25200", "average_win": "125", "average_loss": "-50",
            "win_rate": "0.5", "realized_reward_risk": "2.5",
            "peak_balance": "25200", "max_closed_trade_drawdown": "50",
        }.items():
            self.assertEqual(D(snapshot[name]), D(expected), name)
        self.assertEqual((snapshot["wins"], snapshot["losses"], snapshot["breakevens"]), (2, 1, 1))
        self.assertEqual(snapshot["session_net_pnl"], {"day-1": "200"})

    def test_decimal_precision_and_first_loss_drawdown(self):
        ledger = AccountLedger("a", D("25000"))
        ledger.apply_trade(trade(gross="0.10", commission="0.30"))
        self.assertEqual(D(ledger.snapshot()["balance"]), D("24999.80"))
        self.assertEqual(D(ledger.snapshot()["max_closed_trade_drawdown"]), D("0.20"))

    def test_duplicate_rejection_is_atomic(self):
        ledger = AccountLedger("a", D("25000"))
        ledger.apply_trade(trade())
        before = ledger.snapshot()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ledger.apply_trade(trade())
        self.assertEqual(ledger.snapshot(), before)

    def test_order_and_overlap_rejections_are_atomic(self):
        ledger = AccountLedger("a", D("25000"))
        ledger.apply_trade(trade(2))
        before = ledger.snapshot()
        for invalid in (trade(1), replace(trade(3), source_order=1),
                        replace(trade(3), entry_timestamp=START)):
            with self.subTest(trade=invalid), self.assertRaises(ValueError):
                ledger.apply_trade(invalid)
            self.assertEqual(ledger.snapshot(), before)

    def test_same_timestamp_uses_source_order(self):
        ledger = AccountLedger("a", D("25000"))
        instant = START
        first = replace(trade(), entry_timestamp=instant, exit_timestamp=instant)
        second = replace(first, trade_id="second", source_order=2)
        ledger.apply_trade(first)
        ledger.apply_trade(second)
        self.assertEqual(ledger.snapshot()["trade_count"], 2)
        with self.assertRaises(ValueError):
            ledger.apply_trade(replace(second, trade_id="third"))

        # During fallback, a later instant can have an earlier local clock time.
        fallback = AccountLedger("fallback", D("25000"))
        early = datetime.fromisoformat("2026-11-01T01:50:00-04:00")
        late = datetime.fromisoformat("2026-11-01T01:10:00-05:00")
        fallback.apply_trade(replace(first, entry_timestamp=early, exit_timestamp=early))
        fallback.apply_trade(replace(second, entry_timestamp=late, exit_timestamp=late))
        self.assertEqual(fallback.snapshot()["trade_count"], 2)

    def test_independent_accounts_and_rebased_suffix(self):
        a, b, later = [AccountLedger(name, D("25000")) for name in ("a", "b", "later")]
        trades = [trade(1, "101"), trade(2, "-49", session="day-2"),
                  trade(3, "26", session="day-2")]
        for item in trades:
            a.apply_trade(item)
            b.apply_trade(item)
        for item in trades[1:]:
            later.apply_trade(item)
        standalone = AccountLedger("standalone", D("25000"))
        for item in trades[1:]:
            standalone.apply_trade(item)
        def accounting(ledger):
            return {k: v for k, v in ledger.snapshot().items() if k != "account_id"}
        self.assertEqual(accounting(a), accounting(b))
        self.assertEqual(accounting(later), accounting(standalone))
        self.assertEqual(D(later.snapshot()["balance"]), D("24975"))
        a.apply_trade(trade(4))
        self.assertEqual(b.snapshot()["trade_count"], 3)

    def test_invalid_trade_fields_and_frozen_inputs(self):
        valid = trade()
        for changes in ({"gross_pnl": D("NaN")}, {"gross_pnl": D("Infinity")},
                        {"gross_pnl": 0.1}, {"commission": D("-1")},
                        {"commission": D("Infinity")}, {"quantity": 2},
                        {"quantity": True}, {"source_order": True},
                        {"source_order": -1}, {"trade_id": " "}, {"session_id": ""},
                        {"entry_timestamp": START.replace(tzinfo=None)},
                        {"entry_timestamp": valid.exit_timestamp + timedelta(seconds=1)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(valid, **changes)
        with self.assertRaises(FrozenInstanceError):
            valid.commission = D("0")

    def test_invalid_activation(self):
        for value in (D("0"), D("-1"), D("NaN"), D("Infinity"), 25000.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                AccountLedger("a", value)
        with self.assertRaises(ValueError):
            AccountLedger("", D("25000"))


class LossLimitTests(unittest.TestCase):
    def engine(self, dll="600", floor="24000"):
        return AccountEngine("test", AccountRules(D("25000"), D(floor),
                                                  D(dll) if dll is not None else None))

    def close(self, index=2, session="day-1"):
        return SessionClose(session, START + timedelta(minutes=2 * index + 1), index)

    def test_floor_equality_breaches_and_precedes_dll(self):
        for loss in ("-1000", "-1001"):
            with self.subTest(loss=loss):
                engine = self.engine()
                events = engine.apply_trade(trade(gross=loss, commission="0"))
                self.assertEqual(engine.snapshot()["status"], "breached")
                self.assertFalse(engine.snapshot()["dll_locked"])
                self.assertEqual([e["type"] for e in events],
                                 ["session_started", "trade_applied", "account_breached"])
                json.dumps(events, allow_nan=False)
                self.assertTrue(all(e["account_id"] == "test" for e in events))

    def test_just_above_floor_survives_and_dll_off_is_explicit(self):
        engine = self.engine(dll=None)
        engine.apply_trade(trade(gross="-999.99", commission="0"))
        self.assertEqual(engine.snapshot()["status"], "active")
        self.assertFalse(engine.snapshot()["dll_locked"])
        self.assertIsNone(engine.snapshot()["daily_loss_limit"])

    def test_dll_equality_includes_commission_and_skips_whole_trade(self):
        engine = self.engine()
        engine.apply_trade(trade(gross="-598", commission="1"))  # -599
        self.assertFalse(engine.snapshot()["dll_locked"])
        events = engine.apply_trade(trade(2, gross="0", commission="1"))  # -600
        self.assertEqual(events[-1]["type"], "dll_locked")
        before = engine.snapshot()
        skipped = trade(3, gross="5000", commission="100")
        self.assertEqual(engine.apply_trade(skipped)[-1]["type"], "trade_skipped")
        after = engine.snapshot()
        self.assertEqual(after, {**before, "skipped_trades": 1})
        self.assertEqual(D(after["balance"]), D("24400"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            engine.apply_trade(skipped)
        self.assertEqual(engine.snapshot(), after)

    def test_dll_uses_net_session_pnl_not_peak_or_gross_losses(self):
        engine = self.engine()
        engine.apply_trade(trade(1, "501"))  # +500
        engine.apply_trade(trade(2, "-700", commission="0"))  # session -200
        self.assertFalse(engine.snapshot()["dll_locked"])
        engine.apply_trade(trade(3, "-400", commission="0"))  # session -600
        self.assertTrue(engine.snapshot()["dll_locked"])

    def test_explicit_close_required_and_lock_clears_only_at_next_session(self):
        engine = self.engine()
        engine.apply_trade(trade(gross="-600", commission="0"))
        before = engine.snapshot()
        with self.assertRaisesRegex(ValueError, "close the current"):
            engine.apply_trade(trade(3, session="day-2"))
        self.assertEqual(engine.snapshot(), before)
        engine.close_session(self.close())
        self.assertTrue(engine.snapshot()["dll_locked"])
        self.assertEqual(engine.snapshot()["completed_sessions"], 1)
        events = engine.apply_trade(trade(3, session="day-2"))
        self.assertEqual(events[0]["type"], "session_started")
        self.assertFalse(engine.snapshot()["dll_locked"])
        self.assertEqual(engine.snapshot()["current_session_net_pnl"], "100")
        self.assertEqual(engine.snapshot()["balance"], "24500")

    def test_terminal_trades_and_closes_leave_snapshot_unchanged(self):
        engine = self.engine()
        engine.apply_trade(trade(gross="-1000", commission="0"))
        terminal = engine.snapshot()
        self.assertEqual(engine.apply_trade(trade(2, "9000"))[-1]["type"], "trade_ignored")
        self.assertEqual(engine.snapshot(), terminal)
        self.assertEqual(engine.close_session(self.close(3))[-1]["type"], "session_close_ignored")
        self.assertEqual(engine.snapshot(), terminal)
        self.assertEqual(engine.apply_trade(trade(4, session="day-2"))[-1]["type"], "trade_ignored")
        self.assertEqual(engine.snapshot(), terminal)

    def test_closed_session_and_duplicate_close_rejection_are_atomic(self):
        engine = self.engine()
        engine.apply_trade(trade())
        engine.close_session(self.close())
        before = engine.snapshot()
        for action in (lambda: engine.apply_trade(trade(3)),
                       lambda: engine.close_session(self.close(3))):
            with self.assertRaisesRegex(ValueError, "already closed"):
                action()
            self.assertEqual(engine.snapshot(), before)

    def test_invalid_stream_events_do_not_mutate_account(self):
        engine = self.engine()
        engine.apply_trade(trade(2))
        before = engine.snapshot()
        for action in (
            lambda: engine.apply_trade(trade(1)),
            lambda: engine.apply_trade(replace(trade(3), source_order=2)),
            lambda: engine.apply_trade(replace(trade(3), entry_timestamp=START)),
            lambda: engine.close_session(self.close(1)),
            lambda: engine.close_session(self.close(3, "wrong-session")),
        ):
            with self.assertRaises(ValueError):
                action()
            self.assertEqual(engine.snapshot(), before)

    def test_empty_sessions_close_and_fixed_floor_does_not_trail(self):
        engine = self.engine()
        engine.close_session(self.close(1, "empty"))
        engine.apply_trade(trade(2, "2001", session="profitable"))
        engine.close_session(self.close(3, "profitable"))
        self.assertEqual(engine.snapshot()["completed_sessions"], 2)
        self.assertEqual(engine.snapshot()["loss_floor"], "24000")
        self.assertEqual(engine.snapshot()["balance"], "27000")
        self.assertEqual(engine.snapshot()["status"], "active")  # development account has no target

    def test_accounts_have_independent_locks_and_late_activation(self):
        original, later = self.engine(), self.engine()
        original.apply_trade(trade(1, "-500", commission="0"))
        shared = trade(2, "-100", commission="0")
        original.apply_trade(shared)
        later.apply_trade(shared)
        self.assertTrue(original.snapshot()["dll_locked"])
        self.assertFalse(later.snapshot()["dll_locked"])
        original.apply_trade(trade(3))
        later.apply_trade(trade(3))
        self.assertEqual(original.snapshot()["balance"], "24400")
        self.assertEqual(later.snapshot()["balance"], "25000")

    def test_close_timestamp_ties_use_source_order_and_bound_next_entry(self):
        engine = self.engine()
        first = trade()
        engine.apply_trade(first)
        engine.close_session(SessionClose("day-1", first.exit_timestamp, 2))
        second = replace(trade(3, session="day-2"), entry_timestamp=first.exit_timestamp,
                         exit_timestamp=first.exit_timestamp)
        engine.apply_trade(second)
        self.assertEqual(engine.snapshot()["trade_count"], 2)
        with self.assertRaises(ValueError):
            engine.close_session(SessionClose("day-2", first.exit_timestamp, 3))

    def test_invalid_rules_and_close_fields(self):
        valid = AccountRules(D("25000"), D("24000"), D("600"))
        for changes in ({"starting_capital": D("0")}, {"loss_floor": D("25000")},
                        {"loss_floor": D("-1")}, {"loss_floor": D("NaN")},
                        {"daily_loss_limit": D("0")}, {"daily_loss_limit": D("-1")},
                        {"daily_loss_limit": 600.0}, {"daily_loss_limit": D("Infinity")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(valid, **changes)
        close = self.close()
        for changes in ({"session_id": ""}, {"source_order": True}, {"source_order": -1},
                        {"timestamp": START.replace(tzinfo=None)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(close, **changes)
        with self.assertRaises(FrozenInstanceError):
            valid.loss_floor = D("0")


def stage_rules(stage="evaluation", **changes):
    values = dict(starting_capital=D("25000"), loss_floor=D("24000"), daily_loss_limit=D("600"),
                  account_type=stage, loss_model="eod_trailing", trailing_distance=D("1000"),
                  floor_cap=D("25100"))
    if stage == "evaluation":
        values.update(evaluation_target=D("1250"), consistency_limit=D("0.5"),
                      consistency_policy="strict")
    else:
        values.update(qualifying_day_profit=D("100"))
    values.update(changes)
    return AccountRules(**values)


class SessionRuleTests(unittest.TestCase):
    def day(self, engine, day, net, close=True):
        """One synthetic one-contract trade per session; $1 commission."""
        start = START + timedelta(days=day)
        session = f"session-{day}"
        engine.apply_trade(CompletedTrade(f"t-{day}", start, start + timedelta(minutes=1),
                                          session, day * 2 + 1, 1, D(net) + D("1"), D("1")))
        if close:
            return engine.close_session(SessionClose(session, start + timedelta(hours=1), day * 2 + 2))
        return ()

    def test_trails_only_at_close_from_final_balance_not_intraday_peak(self):
        engine = AccountEngine("a", stage_rules("funded"))
        engine.apply_trade(trade(1, "801"))  # balance 25800, intraday only
        self.assertEqual(engine.snapshot()["loss_floor"], "24000")
        engine.apply_trade(trade(2, "-299"))  # final 25500
        events = engine.close_session(SessionClose("day-1", START + timedelta(hours=1), 3))
        self.assertEqual(engine.snapshot()["loss_floor"], "24500")
        floor = next(e for e in events if e["type"] == "floor_updated")
        self.assertEqual((floor["old_floor"], floor["new_floor"], floor["triggering_balance"]),
                         ("24000", "24500", "25500"))

    def test_floor_never_lowers_and_caps_at_25100(self):
        engine = AccountEngine("a", stage_rules("funded"))
        for day, net, floor in ((0, "800", "24800"), (1, "-200", "24800"),
                                (2, "500", "25100"), (3, "1000", "25100")):
            self.day(engine, day, net)
            self.assertEqual(engine.snapshot()["loss_floor"], floor)
        self.assertEqual(engine.snapshot()["highest_completed_balance"], "27100")

    def test_updated_floor_equality_breaches_with_priority_over_dll(self):
        engine = AccountEngine("a", stage_rules("funded"))
        self.day(engine, 0, "1100")  # locked floor 25100
        start = START + timedelta(days=1)
        events = engine.apply_trade(CompletedTrade("loss", start, start, "next", 3, 1,
                                                   D("-999"), D("1")))
        self.assertEqual(engine.snapshot()["balance"], "25100")
        self.assertEqual(engine.snapshot()["status"], "breached")
        self.assertEqual(events[-1]["type"], "account_breached")
        self.assertFalse(engine.snapshot()["dll_locked"])

    def test_evaluation_target_delayed_by_consistency_then_passes_at_equality(self):
        engine = AccountEngine("a", stage_rules())
        pending = self.day(engine, 0, "1250")
        self.assertEqual(engine.snapshot()["status"], "active")
        self.assertTrue(pending[-1]["target_met"])
        self.assertFalse(pending[-1]["consistency_met"])
        self.day(engine, 1, "625")
        events = self.day(engine, 2, "625")  # 1250 / 2500 == 50%
        self.assertEqual(engine.snapshot()["status"], "passed")
        self.assertEqual(events[-1]["type"], "evaluation_passed")
        self.assertEqual(engine.snapshot()["balance"], "27500")
        terminal = engine.snapshot()
        ignored = self.day(engine, 3, "-2000")
        self.assertEqual(ignored[-1]["type"], "session_close_ignored")
        self.assertEqual(engine.snapshot(), terminal)

    def test_target_boundary_and_consistency_are_both_required(self):
        for second, expected in (("624.99", "active"), ("625", "passed")):
            engine = AccountEngine("a", stage_rules())
            self.day(engine, 0, "625")
            self.day(engine, 1, second)
            self.assertEqual(engine.snapshot()["status"], expected)

    def test_losing_day_reduces_consistency_denominator(self):
        engine = AccountEngine("a", stage_rules())
        self.day(engine, 0, "800")
        self.day(engine, 1, "-200")
        events = self.day(engine, 2, "650")  # 800/1250 > 50%
        self.assertEqual(engine.snapshot()["balance"], "26250")
        self.assertEqual(engine.snapshot()["best_winning_day"], "800")
        self.assertTrue(events[-1]["target_met"])
        self.assertFalse(events[-1]["consistency_met"])
        self.assertEqual(engine.snapshot()["status"], "active")

    def test_zero_or_negative_profit_does_not_pass(self):
        engine = AccountEngine("a", stage_rules())
        for day, net in ((0, "0"), (1, "-100")):
            events = self.day(engine, day, net)
            self.assertFalse(events[-1]["consistency_met"])
            self.assertEqual(engine.snapshot()["status"], "active")

    def test_unclosed_last_session_never_passes_or_trails(self):
        engine = AccountEngine("a", stage_rules())
        self.day(engine, 0, "625")
        self.day(engine, 1, "625", close=False)
        before = engine.snapshot()
        events = engine.finish_data()
        after = engine.snapshot()
        self.assertEqual(after, {**before, "data_finished": True, "outcome": "unfinished"})
        self.assertEqual(after["completed_sessions"], 1)
        self.assertEqual(after["loss_floor"], "24625")
        self.assertEqual(events[0]["outcome"], "unfinished")
        self.assertEqual(engine.finish_data(), ())
        self.assertEqual(engine.snapshot(), after)
        with self.assertRaisesRegex(ValueError, "data already finished"):
            engine.close_session(SessionClose("session-1", START + timedelta(days=2), 9))
        with self.assertRaisesRegex(ValueError, "data already finished"):
            engine.apply_trade(trade(10))

    def test_funded_qualifying_equality_losing_empty_and_unclosed_days(self):
        engine = AccountEngine("a", stage_rules("funded"))
        self.day(engine, 0, "99.99")
        self.day(engine, 1, "100")
        self.day(engine, 2, "-50")
        engine.close_session(SessionClose("empty", START + timedelta(days=3), 7))
        self.day(engine, 4, "100", close=False)
        engine.finish_data()
        snapshot = engine.snapshot()
        self.assertEqual(snapshot["qualifying_days"], 1)
        self.assertEqual(snapshot["completed_sessions"], 4)
        self.assertEqual(snapshot["best_winning_day"], "100")
        self.assertEqual(snapshot["status"], "active")
        self.assertEqual(snapshot["outcome"], "unfinished")

    def test_funded_five_qualifying_days_do_not_imply_payout_or_evaluation_pass(self):
        engine = AccountEngine("a", stage_rules("funded"))
        for day in range(5):
            self.day(engine, day, "500")
        self.assertEqual(engine.snapshot()["qualifying_days"], 5)
        self.assertEqual(engine.snapshot()["status"], "active")
        self.assertNotIn("payout_eligible", engine.snapshot())
        engine.finish_data()
        self.assertEqual(engine.snapshot()["outcome"], "unfinished")

    def test_finished_empty_and_terminal_outcomes(self):
        empty = AccountEngine("empty", stage_rules("funded"))
        self.assertIsNone(empty.finish_data()[0]["timestamp"])
        self.assertEqual(empty.snapshot()["completed_sessions"], 0)
        for amount, expected in (("-1000", "breached"), ("625", "passed")):
            engine = AccountEngine("a", stage_rules())
            self.day(engine, 0, amount)
            if expected == "passed":
                self.day(engine, 1, "625")
            self.assertEqual(engine.finish_data()[0]["outcome"], expected)
            self.assertEqual(engine.snapshot()["status"], expected)

    def test_invalid_or_unsupported_stage_and_trailing_rules(self):
        valid = stage_rules()
        for changes in ({"loss_model": "intraday"}, {"account_type": "unknown"},
                        {"trailing_distance": None}, {"trailing_distance": D("0")},
                        {"trailing_distance": D("999")}, {"floor_cap": D("23999")},
                        {"floor_cap": D("NaN")}, {"evaluation_target": None},
                        {"evaluation_target": D("0")}, {"consistency_limit": D("0")},
                        {"consistency_limit": D("1.01")}, {"consistency_policy": None},
                        {"consistency_policy": "cushion"}, {"account_type": "funded"},
                        {"loss_model": "fixed"}, {"qualifying_day_profit": D("0")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(valid, **changes)
        with self.assertRaisesRegex(ValueError, "require qualifying"):
            replace(stage_rules("funded"), qualifying_day_profit=None)


if __name__ == "__main__":
    unittest.main()
