import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from replay import load_config, number, replay_rows, rows, session_day, simulate, stamp, validate

CONFIG = Path(__file__).resolve().parents[1] / "configs/lucidflex_25k_provisional.json"


def observation(day, gross, unrealized=0, position=0, costs=0, hour=10, seq=1):
    return {"timestamp": f"2026-01-{day:02}T{hour:02}:00:00.0000000-05:00", "event_sequence": seq,
            "gross_realized": str(gross), "unrealized": str(unrealized), "position": position,
            "costs": str(costs), "source": "BarClose"}


def fixture(root):
    """Hand-calculated $20 gross/$19 cost-adjusted unit trade, independent of real exports."""
    def timestamp(hour):
        return f"2026-01-02T{hour:02}:00:00-05:00"

    def write(name, records):
        fields = list(dict.fromkeys(k for r in records for k in r))
        with (root / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

    base = {"run_id": "fixture", "instrument": "MNQ TEST"}
    metadata = dict(base, completion_status="Finalized", usable=True, accounting_complete=True, error=None,
                    schema_version="1.0", point_value=2, source_timezone="Eastern Standard Time",
                    strategy_parameters={"AllowLayering": "False"}, initial_strategy_quantity=0,
                    final_signed_position_quantity=0, final_open_lots=[], execution_count=2,
                    final_gross_realized_pnl=20, closed_segment_count=1, last_event_sequence=8,
                    bar_count=2, last_tick_count=0, observed_start=timestamp(9), observed_end=timestamp(17))
    (root / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    executions = []
    for seq, hour, side, price, realized, position, average, identity in ((3, 10, "Buy", 100, 0, 1, 100, "entry"), (5, 11, "Sell", 110, 20, 0, "", "exit")):
        executions.append(dict(base, event_sequence=seq, timestamp=timestamp(hour), execution_id=identity,
                               execution_phase="Historical", order_id=identity, account_name="Backtest",
                               execution_side=side, execution_quantity=1, execution_price=price,
                               realized_pnl=realized, signed_position_quantity_after_execution=position,
                               position_quantity_after_execution=position, average_position_price_after_execution=average))
    write("executions.csv", executions)
    write("trades.csv", [dict(base, event_sequence=5, trade_id="t1", entry_execution_id="entry", exit_execution_id="exit",
                              entry_timestamp=timestamp(10), exit_timestamp=timestamp(11), direction="Long", quantity=1,
                              entry_price=100, exit_price=110, gross_realized_pnl=20, entry_signal="ENTRY", raw_exit_name="EXIT")])
    write("equity.csv", [dict(base, event_sequence=seq, timestamp=timestamp(hour), signed_position_quantity=position,
                              average_position_price=average, mark_price=price, cumulative_gross_realized_pnl=gross,
                              unrealized_pnl=0, gross_equity_change=gross, observation_source=source)
                         for seq, hour, position, average, price, gross, source in (
                             (2, 9, 0, "", 100, 0, "BarClose"), (4, 10, 1, 100, 100, 0, "Execution"),
                             (6, 11, 0, "", 110, 20, "Execution"), (8, 17, 0, "", 110, 20, "BarClose"))])
    write("bars.csv", [dict(base, event_sequence=seq, timestamp=timestamp(hour), open=price, high=price,
                            low=price, close=price, volume=1) for seq, hour, price in ((1, 9, 100), (7, 17, 110))])
    analyzer = {"Trade number": 1, "Instrument": "MNQ TEST", "Market pos.": "Long", "Qty": 1,
                "Entry price": 100, "Exit price": 110, "Entry time": "01/02/2026 10:00:00",
                "Exit time": "01/02/2026 11:00:00", "Entry name": "ENTRY", "Exit name": "EXIT", "Profit": "$20.00"}
    analyzer.update({k: "$0.00" for k in ("Commission", "Clearing Fee", "Exchange Fee", "IP Fee", "NFA Fee")})
    write("analyzer-trades.csv", [analyzer])
    write("analyzer-summary.csv", [{"Performance": key, "All trades": value} for key, value in (
        ("Total net profit", "$20.00"), ("Commission", "$0.00"), ("Total # of trades", "1"), ("Gross profit", "$20.00"), ("Gross loss", "$0.00"))])


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)

    def test_loss_floor_equality_breaches(self):
        result, events = simulate([observation(2, 0), observation(2, -1000)], self.config)
        self.assertEqual(result["outcome"], "breach")
        self.assertEqual(events[-1]["equity"], events[-1]["loss_floor"])

    def test_cost_on_open_position_can_breach(self):
        result, _ = simulate([observation(2, 0), observation(2, -999, -D("0.5"), -1, D("0.5"))], self.config)
        self.assertEqual(result["outcome"], "breach")
        self.assertEqual(result["position_at_stop"], -1)

    def test_eod_ratchets_never_loosen_or_follow_intraday_peak(self):
        config = dict(self.config, profit_target=D(10000))
        data = [observation(2, 0), observation(2, 0, 5000, 1), observation(2, 500),
                observation(3, 500), observation(3, 400), observation(4, 400)]
        result, events = simulate(data, config)
        self.assertEqual(result["loss_floor"], D(24500))
        self.assertEqual([e["loss_floor"] for e in events if e["event"] == "session_closed"], [D(24500), D(24500)])

    def test_floor_cap(self):
        config = dict(self.config, profit_target=D(10000))
        result, _ = simulate([observation(2, 0), observation(2, 3000), observation(3, 3000)], config)
        self.assertEqual(result["loss_floor"], D(25100))

    def test_pass_requires_consistency_and_observed_rollover(self):
        data = [observation(2, 0), observation(2, 500), observation(3, 500), observation(3, 1000),
                observation(4, 1000), observation(4, 1250)]
        partial, _ = simulate(data, self.config)
        self.assertEqual(partial["outcome"], "incomplete")
        result, events = simulate(data + [observation(5, 1250)], self.config)
        self.assertEqual(result["outcome"], "pass")
        self.assertEqual(events[-1]["consistency_ratio"], D("0.4"))
        self.assertEqual(result["ending_timestamp"], data[-1]["timestamp"])

    def test_consistency_blocks_until_more_profit(self):
        data = [observation(2, 0), observation(2, 600), observation(3, 600), observation(3, 1000),
                observation(4, 1000), observation(4, 1400), observation(5, 1400)]
        self.assertEqual(simulate(data, self.config)[0]["outcome"], "incomplete")
        data += [observation(5, 1600), observation(6, 1600)]
        self.assertEqual(simulate(data, self.config)[0]["outcome"], "pass")

    def test_future_gain_cannot_erase_breach(self):
        result, _ = simulate([observation(2, 0), observation(2, -1000), observation(3, 10000)], self.config)
        self.assertEqual(result["outcome"], "breach")
        self.assertEqual(result["ending_balance"], D(24000))

    def test_overnight_position_rejected(self):
        with self.assertRaisesRegex(ValueError, "Overnight"):
            simulate([observation(2, 0), observation(2, 0, 0, 1), observation(3, 0)], self.config)

    def test_timezone_and_precision(self):
        self.assertEqual(stamp("2026-01-02T09:55:00.1234567-05:00").microsecond, 123456)
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            stamp("2026-11-01T01:30:00")
        for offset in ("-05:00", "-04:00"):
            self.assertEqual(session_day(f"2026-01-02T18:00:00{offset}", self.config), "2026-01-03")
            self.assertEqual(session_day(f"2026-01-02T17:59:00{offset}", self.config), "2026-01-02")

    def test_bad_numbers_and_wrong_export_rejected(self):
        for value in ("", "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                number(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            path.write_text("Period,Net profit\n01/02/2026,150\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing columns"):
                list(rows(path, ["Entry time"]))

    def test_fixed_costs_use_sequence_and_not_logged_net(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            fields = ["run_id", "instrument", "timestamp", "event_sequence", "signed_position_quantity",
                      "cumulative_gross_realized_pnl", "unrealized_pnl", "observation_source", "net_equity_change"]
            with (path / "equity.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for seq, position, gross in ((1, 0, 0), (3, 1, 0), (5, 0, 100)):
                    writer.writerow(dict(zip(fields, ["test", "MNQ TEST", "2026-01-02T10:00:00-05:00", seq, position, gross, 0, "Execution" if seq > 1 else "BarClose", -999])))
            fills = [{"event_sequence": "2", "execution_quantity": "1"}, {"event_sequence": "4", "execution_quantity": "1"}]
            result = list(replay_rows(path, {"run_id": "test", "instrument": "MNQ TEST"}, fills, self.config))
            self.assertEqual([r["costs"] for r in result], [D(0), D("0.5"), D(1)])
            self.assertEqual(result[-1]["gross_realized"], "100")

    def test_end_to_end_validation_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            metadata, executions, report = validate(root, root / "analyzer-trades.csv", root / "analyzer-summary.csv", self.config)
            self.assertEqual(report["gross_pnl"], D(20))
            self.assertEqual(report["assumed_commissions_full_run"], D(1))
            self.assertEqual(report["daily_net_pnl_under_assumption"], {"2026-01-02": D(19)})
            result, _ = simulate(replay_rows(root, metadata, executions, self.config), self.config)
            self.assertEqual(result["outcome"], "incomplete")
            self.assertEqual(result["ending_balance"], D(25019))
            path = root / "analyzer-trades.csv"
            path.write_text(path.read_text().replace("$20.00", "$21.00"))
            with self.assertRaisesRegex(ValueError, "profit"):
                validate(root, path, root / "analyzer-summary.csv", self.config)

    def test_equity_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            path = root / "equity.csv"
            path.write_text(path.read_text().replace(",110,20,0,20,Execution", ",110,20,0,21,Execution"))
            with self.assertRaisesRegex(ValueError, "Equity gross change"):
                validate(root, root / "analyzer-trades.csv", root / "analyzer-summary.csv", self.config)


if __name__ == "__main__":
    unittest.main()
