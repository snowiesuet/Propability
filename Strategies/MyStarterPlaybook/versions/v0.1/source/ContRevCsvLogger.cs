using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies
{
    public enum ContRevCommissionMode { Unknown, Platform, FixedPerContractPerSide }

    // No NinjaTrader dependencies: all input is snapshotted by the strategy adapter.
    internal sealed class ContRevFill
    {
        public string ExecutionId, OrderId, OrderName, EntrySignal, Account, MarketPosition, Phase, Side;
        public DateTime Time;
        public string TradingDay;
        public int Quantity, Sign;
        public double Price;
        public double? PlatformCommission;
        public string Quality = "Observed";
    }

    internal sealed class ContRevCsvLogger
    {
        private sealed class Lot
        {
            public ContRevFill Fill;
            public int Remaining, Sign;
            public string PositionId;
            public double? CommissionPerUnit;
            public double Favorable, Adverse;
            public int Marks;
        }

        private readonly Dictionary<string, object> metadata;
        private readonly Dictionary<string, StreamWriter> writers = new Dictionary<string, StreamWriter>();
        private readonly List<Lot> lots = new List<Lot>();
        private readonly HashSet<string> executionKeys = new HashSet<string>();
        private readonly TimeZoneInfo zone;
        private readonly ContRevCommissionMode commissionMode;
        private readonly double fixedCommission, pointValue;
        private readonly string strategy, instrument;
        private long sequence, positionNumber, tradeNumber, barCount, tickCount, historicalTickCount, fillCount, duplicates;
        private double realized, commissions;
        private bool costsKnown = true, accountingComplete = true, closed;
        private DateTime? firstTime, lastTime;
        public readonly string RunId, DirectoryPath;

        public ContRevCsvLogger(string root, string strategyName, string instrumentName, double value,
            TimeZoneInfo sourceZone, ContRevCommissionMode mode, double rate, Dictionary<string, object> runMetadata)
        {
            if (!Finite(value) || value <= 0 || !Finite(rate) || rate < 0)
                throw new ArgumentException("Invalid point value or logging commission rate.");
            strategy = strategyName; instrument = instrumentName; pointValue = value;
            zone = sourceZone; commissionMode = mode; fixedCommission = rate; metadata = runMetadata;
            RunId = DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffffffZ", CultureInfo.InvariantCulture) + "_" + Guid.NewGuid().ToString("N");
            DirectoryPath = Path.Combine(root, RunId);
            System.IO.Directory.CreateDirectory(DirectoryPath);
            metadata["schema_version"] = "1.0"; metadata["run_id"] = RunId;
            metadata["source_timezone"] = zone == null ? null : zone.Id;
            metadata["commission_mode"] = mode.ToString(); metadata["fixed_commission_per_contract_per_side"] = rate;
            metadata["pnl_currency_basis"] = "Instrument currency; no currency conversion";
            try
            {
                WriteMetadata("Running", null);
                Open("executions", "run_id,strategy_name,instrument,account_name,execution_id,order_id,order_name,timestamp,trading_day,market_position,execution_side,execution_quantity,execution_price,commission,realized_pnl,position_quantity_after_execution,average_position_price_after_execution,event_sequence,position_id,signed_position_quantity_after_execution,execution_phase,commission_source,commission_status,data_quality,entry_signal,previous_position_id");
                Open("trades", "run_id,trade_id,instrument,direction,entry_timestamp,exit_timestamp,entry_price,exit_price,quantity,gross_realized_pnl,commissions,net_realized_pnl,maximum_favorable_excursion,maximum_adverse_excursion,exit_reason,entry_signal,trading_day,position_id,entry_execution_id,exit_execution_id,entry_order_id,exit_order_id,entry_trading_day,commission_source,commission_status,excursion_sampling_quality,raw_exit_name,event_sequence");
                Open("equity", "run_id,instrument,timestamp,trading_day,event_sequence,observation_source,execution_phase,signed_position_quantity,average_position_price,mark_price,cumulative_gross_realized_pnl,cumulative_commissions,cumulative_net_realized_pnl,unrealized_pnl,gross_equity_change,net_equity_change,data_quality,position_id");
                Open("bars", "run_id,instrument,timestamp,trading_day,event_sequence,execution_phase,open,high,low,close,volume,data_quality");
            }
            catch { foreach (var writer in writers.Values) { try { writer.Dispose(); } catch { } } throw; }
        }

        private void Open(string name, string header)
        {
            var writer = new StreamWriter(new FileStream(Path.Combine(DirectoryPath, name + ".csv"), FileMode.CreateNew, FileAccess.Write, FileShare.Read), new UTF8Encoding(false));
            writers.Add(name, writer); writer.WriteLine(header);
        }

        public static bool Finite(double x) { return !double.IsNaN(x) && !double.IsInfinity(x); }
        private int SignedQuantity { get { return lots.Sum(x => x.Remaining * x.Sign); } }
        private double? AveragePrice { get { return lots.Count == 0 ? (double?)null : lots.Sum(x => x.Fill.Price * x.Remaining) / lots.Sum(x => x.Remaining); } }
        private string PositionId { get { return lots.Count == 0 ? null : lots[0].PositionId; } }
        private string CostSource { get { return commissionMode.ToString(); } }

        public string Timestamp(DateTime value)
        {
            // NT callback timestamps are wall times in its configured timezone. Never use host timezone.
            var wall = DateTime.SpecifyKind(value, DateTimeKind.Unspecified);
            if (zone == null || zone.IsAmbiguousTime(wall) || zone.IsInvalidTime(wall))
                return wall.ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff", CultureInfo.InvariantCulture);
            return new DateTimeOffset(wall, zone.GetUtcOffset(wall)).ToString("o", CultureInfo.InvariantCulture);
        }

        private string TimeQuality(DateTime time)
        {
            var wall = DateTime.SpecifyKind(time, DateTimeKind.Unspecified);
            return zone == null || zone.IsAmbiguousTime(wall) || zone.IsInvalidTime(wall) ? ";TimezoneUnresolved" : "";
        }

        private void ObserveTime(DateTime time)
        {
            if (!firstTime.HasValue || time < firstTime.Value) firstTime = time;
            if (!lastTime.HasValue || time > lastTime.Value) lastTime = time;
        }

        public void Execution(ContRevFill fill)
        {
            if (closed) return;
            if (fill.Quantity <= 0 || !Finite(fill.Price)) throw new ArgumentException("Invalid execution quantity/price.");
            // ID scope includes phase so historical IDs cannot hide realtime fills.
            if (!string.IsNullOrEmpty(fill.ExecutionId))
            {
                string key = Json(new object[] { fill.Phase, instrument, fill.Account, fill.OrderId, fill.ExecutionId });
                if (!executionKeys.Add(key)) { duplicates++; return; }
            }
            else fill.Quality += ";ExecutionIdentityUnavailable";
            fillCount++; ObserveTime(fill.Time);
            long eventId = ++sequence;
            double? cost = null;
            if (commissionMode == ContRevCommissionMode.FixedPerContractPerSide) cost = fixedCommission * fill.Quantity;
            if (commissionMode == ContRevCommissionMode.Platform && fill.PlatformCommission.HasValue && Finite(fill.PlatformCommission.Value) && fill.PlatformCommission.Value >= 0) cost = fill.PlatformCommission;
            if (cost.HasValue) commissions += cost.Value; else costsKnown = false;
            string previousPosition = PositionId;
            double? increment = accountingComplete ? (double?)0 : null;
            if (fill.Sign != 1 && fill.Sign != -1) { accountingComplete = false; increment = null; fill.Quality += ";DirectionUnresolved"; }
            if (accountingComplete)
            {
                Mark(fill.Price); // Fill is an observed mark for all lots already open.
                int remaining = fill.Quantity;
                bool reversing = SignedQuantity != 0 && Math.Sign(SignedQuantity) != fill.Sign && fill.Quantity > Math.Abs(SignedQuantity);
                while (remaining > 0 && lots.Count > 0 && lots[0].Sign != fill.Sign)
                {
                    Lot lot = null;
                    if (!string.IsNullOrEmpty(fill.EntrySignal)) lot = lots.FirstOrDefault(x => x.Fill.EntrySignal == fill.EntrySignal);
                    if (lot == null)
                    {
                        lot = lots[0];
                        if (!string.IsNullOrEmpty(fill.EntrySignal)) fill.Quality += ";SignalMatchFallbackFIFO";
                    }
                    int quantity = Math.Min(remaining, lot.Remaining);
                    double gross = (fill.Price - lot.Fill.Price) * lot.Sign * quantity * pointValue;
                    double? segmentCost = lot.CommissionPerUnit.HasValue && cost.HasValue ? (lot.CommissionPerUnit.Value + cost.Value / fill.Quantity) * quantity : (double?)null;
                    Row("trades", RunId, RunId + "_t" + (++tradeNumber), instrument, lot.Sign > 0 ? "Long" : "Short",
                        Timestamp(lot.Fill.Time), Timestamp(fill.Time), lot.Fill.Price, fill.Price, quantity, gross, segmentCost,
                        segmentCost.HasValue ? (double?)(gross - segmentCost.Value) : null,
                        lot.Favorable * quantity * pointValue, lot.Adverse * quantity * pointValue,
                        ExitReason(fill.OrderName, reversing), lot.Fill.EntrySignal, fill.TradingDay, lot.PositionId,
                        lot.Fill.ExecutionId, fill.ExecutionId, lot.Fill.OrderId, fill.OrderId, lot.Fill.TradingDay,
                        CostSource, segmentCost.HasValue ? "Known" : "Unknown", "ObservedMarksApproximate" + TimeQuality(fill.Time) + TimeQuality(lot.Fill.Time), fill.OrderName, eventId);
                    increment += gross; realized += gross; remaining -= quantity; lot.Remaining -= quantity;
                    if (lot.Remaining == 0) lots.Remove(lot);
                }
                if (remaining > 0)
                {
                    string id = PositionId ?? RunId + "_p" + (++positionNumber);
                    lots.Add(new Lot { Fill = fill, Remaining = remaining, Sign = fill.Sign, PositionId = id,
                        CommissionPerUnit = cost.HasValue ? (double?)(cost.Value / fill.Quantity) : null });
                }
            }
            string quality = fill.Quality + TimeQuality(fill.Time) + (accountingComplete ? "" : ";AccountingIncomplete");
            Row("executions", RunId, strategy, instrument, fill.Account, fill.ExecutionId, fill.OrderId, fill.OrderName,
                Timestamp(fill.Time), fill.TradingDay, fill.MarketPosition, fill.Side, fill.Quantity, fill.Price, cost, increment,
                accountingComplete ? (int?)Math.Abs(SignedQuantity) : null, accountingComplete ? AveragePrice : null,
                eventId, PositionId ?? previousPosition, accountingComplete ? (int?)SignedQuantity : null, fill.Phase,
                CostSource, cost.HasValue ? "Known" : "Unknown", quality, fill.EntrySignal, previousPosition);
            Equity(fill.Time, fill.TradingDay, fill.Price, "Execution", fill.Phase);
        }

        private static string ExitReason(string name, bool reversal)
        {
            string text = (name ?? "").ToLowerInvariant();
            if (text.Contains("session close")) return "SessionClose";
            if (text.Contains("stop loss")) return "StopLoss";
            if (text.Contains("profit target")) return "ProfitTarget";
            return reversal || text.Contains("close position") ? "Reversal" : "Unknown";
        }

        private void Mark(double price)
        {
            foreach (var lot in lots)
            {
                double move = (price - lot.Fill.Price) * lot.Sign;
                lot.Favorable = Math.Max(lot.Favorable, move); lot.Adverse = Math.Max(lot.Adverse, -move); lot.Marks++;
            }
        }

        public void Bar(DateTime time, string day, string phase, double open, double high, double low, double close, double volume)
        {
            if (closed) return;
            barCount++; ObserveTime(time);
            Row("bars", RunId, instrument, Timestamp(time), day, ++sequence, phase, open, high, low, close, volume, "OHLC_NoIntrabarOrdering" + TimeQuality(time));
            Equity(time, day, close, "BarClose", phase); Flush();
        }

        public void Tick(DateTime time, string day, string phase, double price)
        {
            if (closed) return;
            tickCount++; if (phase == "Historical") historicalTickCount++;
            Equity(time, day, price, "Last", phase);
        }

        private void Equity(DateTime time, string day, double price, string source, string phase)
        {
            if (!Finite(price)) throw new ArgumentException("Invalid mark price.");
            ObserveTime(time); if (accountingComplete) Mark(price);
            double? unrealized = accountingComplete ? (double?)lots.Sum(x => (price - x.Fill.Price) * x.Sign * x.Remaining * pointValue) : null;
            Row("equity", RunId, instrument, Timestamp(time), day, ++sequence, source, phase,
                accountingComplete ? (int?)SignedQuantity : null, accountingComplete ? AveragePrice : null, price,
                accountingComplete ? (double?)realized : null, costsKnown ? (double?)commissions : null,
                accountingComplete && costsKnown ? (double?)(realized - commissions) : null, unrealized,
                unrealized.HasValue ? (double?)(realized + unrealized.Value) : null,
                unrealized.HasValue && costsKnown ? (double?)(realized - commissions + unrealized.Value) : null,
                (accountingComplete ? "ObservedMarkApproximate" : "AccountingIncomplete") + TimeQuality(time), PositionId);
        }

        public void Flush() { foreach (var writer in writers.Values) writer.Flush(); }

        public void Finish(string error)
        {
            if (closed) return;
            closed = true;
            var failures = new List<string>();
            if (error != null) failures.Add(error);
            foreach (var writer in writers.Values)
            {
                try { writer.Dispose(); } catch (Exception ex) { failures.Add(ex.Message); }
            }
            WriteMetadata(failures.Count == 0 ? "Finalized" : "Failed", failures.Count == 0 ? null : string.Join(" | ", failures.ToArray()));
        }

        private void WriteMetadata(string status, string error)
        {
            metadata["completion_status"] = status; metadata["error"] = error;
            metadata["usable"] = status == "Finalized" && accountingComplete;
            metadata["accounting_complete"] = accountingComplete; metadata["commissions_complete"] = costsKnown;
            metadata["observed_start"] = firstTime.HasValue ? Timestamp(firstTime.Value) : null;
            metadata["observed_end"] = lastTime.HasValue ? Timestamp(lastTime.Value) : null;
            metadata["bar_count"] = barCount; metadata["last_tick_count"] = tickCount; metadata["historical_last_tick_count"] = historicalTickCount;
            metadata["execution_count"] = fillCount; metadata["duplicate_execution_count"] = duplicates;
            metadata["closed_segment_count"] = tradeNumber; metadata["last_event_sequence"] = sequence;
            metadata["sampling_coverage"] = historicalTickCount == 0 ? "HistoricalBarsOnly_NoIntrabarBreachOrdering" : "ObservedLastTicks_NotGuaranteedComplete";
            metadata["final_signed_position_quantity"] = accountingComplete ? (int?)SignedQuantity : null;
            metadata["final_average_position_price"] = accountingComplete ? AveragePrice : null;
            metadata["final_gross_realized_pnl"] = accountingComplete ? (double?)realized : null;
            metadata["final_commissions"] = costsKnown ? (double?)commissions : null;
            metadata["final_open_lots"] = lots.Select(x => (object)new Dictionary<string, object> {
                { "position_id", x.PositionId }, { "execution_id", x.Fill.ExecutionId }, { "order_id", x.Fill.OrderId },
                { "entry_signal", x.Fill.EntrySignal }, { "quantity", x.Remaining }, { "sign", x.Sign },
                { "entry_price", x.Fill.Price }, { "entry_timestamp", Timestamp(x.Fill.Time) },
                { "remaining_entry_commission", x.CommissionPerUnit.HasValue ? (double?)(x.CommissionPerUnit.Value * x.Remaining) : null }
            }).ToArray();
            // Replace only after a full new metadata document has been written.
            string path = Path.Combine(DirectoryPath, "run_metadata.json");
            string temporary = path + ".tmp";
            File.WriteAllText(temporary, Json(metadata), new UTF8Encoding(false));
            if (File.Exists(path)) File.Replace(temporary, path, null, true); else File.Move(temporary, path);
        }

        private void Row(string file, params object[] values)
        {
            writers[file].WriteLine(string.Join(",", values.Select(Csv).ToArray()));
        }

        private static string Csv(object value)
        {
            if (value == null) return "";
            string text = value is double ? ((double)value).ToString("R", CultureInfo.InvariantCulture) : Convert.ToString(value, CultureInfo.InvariantCulture);
            return text.IndexOfAny(new[] { ',', '"', '\r', '\n' }) >= 0 ? "\"" + text.Replace("\"", "\"\"") + "\"" : text;
        }

        private static string Json(object value)
        {
            if (value == null) return "null";
            if (value is string)
            {
                var result = new StringBuilder("\"");
                foreach (char c in (string)value)
                {
                    if (c == '"' || c == '\\') result.Append('\\').Append(c);
                    else if (c < 32) result.Append("\\u").Append(((int)c).ToString("x4"));
                    else result.Append(c);
                }
                return result.Append('"').ToString();
            }
            var dictionary = value as IDictionary<string, object>;
            if (dictionary != null) return "{" + string.Join(",", dictionary.Select(x => Json(x.Key) + ":" + Json(x.Value)).ToArray()) + "}";
            var array = value as IEnumerable;
            if (array != null) { var items = new List<string>(); foreach (var item in array) items.Add(Json(item)); return "[" + string.Join(",", items.ToArray()) + "]"; }
            if (value is bool) return (bool)value ? "true" : "false";
            if (value is double && !Finite((double)value)) return "null";
            return Convert.ToString(value, CultureInfo.InvariantCulture);
        }
    }
}
