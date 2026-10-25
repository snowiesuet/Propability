// NinjaTrader 8 Strategy
// JJ Simon Fair Value Theory - NQ Opening Continuation / Reversion
//
// Updated to align with the current PDF notes:
// - 1m NQ, entries roughly 9:30-11:00 NY time.
// - Fair value is anchored near the 9:30 market-open price.
// - First ~10-15 minutes: continuation away from fair value.
// - After that: mean reversion back to fair value.
// - Entry model: displacement candle + BOS/MSB.
// - Standard risk = 25 points, target = 37.5 points (1.5R).
// - Optional volatility adjustment: higher ATR uses wider SL/TP.
//
// Recommended: run on NQ 1-minute data first.

#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.Gui.Tools;
using System.Windows.Media;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NYOpenFairPriceStrategy : Strategy
    {
        private readonly object csvLogGate = new object();
        private ContRevCsvLogger csvLogger;
        private SessionIterator csvSessionIterator;
        private bool csvLoggingFailed;
        private string csvLogStage = "Idle";

        private double fairPrice;
        private double openingHigh;
        private double openingLow;
        private double openingClose;

        private bool openingBullish;
        private bool openingBearish;
        private bool continuationInvalid;
        private bool continuationTaken;

        private int tradeCount;
        private int activeEntryBar = -1;
        private int debugTradeNumber;
        private int openingBarIndex = -1;

        // Used to prevent repeated signals from the same lookback structure.
        private double lastBullishStructure = double.NaN;
        private double lastBearishStructure = double.NaN;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "NYOpenFairPriceStrategy";
                Description = "Backtest approximation of the NY-open fair-price continuation/reversion strategy.";

                Calculate = Calculate.OnBarClose;

                // Allows layering when AllowLayering=true.
                EntriesPerDirection = 10;
                EntryHandling = EntryHandling.UniqueEntries;

                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;

                BarsRequiredToTrade = 20;
                IsInstantiatedOnEachOptimizationIteration = true;

                OpenHour = 9;
                OpenMinute = 30;

                ContinuationMinutes = 15;
                ReversionMinutes = 90;

                ConfirmationBars = 3;

                StructureLookback = 5;

                DisplacementMultiplier = 1.20;
                MaxWickPercent = 20.0;

                MinDistanceFromFair = 10.0;

                // PDF guidance: a decisive displacement candle with a small counter-wick
                // is preferred, especially when waiting for BOS would leave too little
                // room to fair value.
                DisplacementOverrideDistance = 38.0;

                StopPoints = 25.0;
                TargetPoints = 37.5;

                ReversionTargetMode = ReversionTargetModeEnum.FixedPoints;

                MaxTradesPerSession = 4;
                AllowLayering = false;
                DebugVisuals = true;

                EnableCsvLogging = false;
                CsvLogOutputRoot = string.Empty;
                CsvCommissionMode = ContRevCommissionMode.Unknown;
                CsvCommissionPerContractPerSide = 0;
            }
            else if (State == State.Terminated)
            {
                CsvLogSafely(delegate { if (csvLogger != null) { csvLogStage = "Finalize output"; csvLogger.Finish(null); } });
            }
        }

        protected override void OnBarUpdate()
        {
            // Instrumentation runs even when the unchanged trading guards below return.
            if (EnableCsvLogging && BarsInProgress == 0 && CurrentBar >= 0)
                CsvLogSafely(delegate
                {
                    csvLogStage = "Initialize on first primary bar";
                    if (csvLogger == null) CsvInitializeLogger();
                    csvLogStage = "Write primary bar";
                    if (csvLogger != null) csvLogger.Bar(Time[0], CsvTradingDay(Time[0]), State.ToString(),
                        Open[0], High[0], Low[0], Close[0], Volume[0]);
                });

            if (CurrentBar < BarsRequiredToTrade)
                return;

            int hh = ToTime(Time[0]) / 10000;
            int mm = (ToTime(Time[0]) / 100) % 100;

            int nowMinutes = hh * 60 + mm;
            int openMinutes = OpenHour * 60 + OpenMinute;
            int elapsed = nowMinutes - openMinutes;

            // Keep the debug levels bounded to the current session/phase.
            // This is intentionally updated each bar so the line ends at the
            // current bar rather than extending across the entire chart.
            if (DebugVisuals &&
                openingBarIndex >= 0 &&
                elapsed >= 0 &&
                elapsed < ReversionMinutes)
            {
                DrawDebugSessionLevels();
            }

            // 9:30 bar: Close[1] is the 9:29 close on a 1-minute chart.
            bool isOpenBar = hh == OpenHour && mm == OpenMinute;

            if (isOpenBar)
            {
                // PDF guidance points to the 9:30 market-open price as the fair-value anchor.
                fairPrice = Open[0];

                openingHigh = High[0];
                openingLow = Low[0];
                openingClose = Close[0];

                openingBullish = openingClose > Open[0];
                openingBearish = openingClose < Open[0];

                continuationInvalid = false;
                continuationTaken = false;

                tradeCount = 0;

                lastBullishStructure = double.NaN;
                lastBearishStructure = double.NaN;

                activeEntryBar = -1;
                debugTradeNumber = 0;
                openingBarIndex = CurrentBar;

                if (DebugVisuals)
                {
                    // Draw only a bounded segment for this session. HorizontalLine
                    // would extend across the entire chart and make multi-day
                    // debugging unreadable.
                    DrawDebugSessionLevels();
                }
            }

            // Only trade after the opening candle and before the reversion cutoff.
            if (elapsed <= 0 || elapsed >= ReversionMinutes)
                return;

            // ---------------------------------------------------------------
            // Opening continuation invalidation
            // ---------------------------------------------------------------
            //
            // Red open: breaking the opening high invalidates the original
            // bearish continuation idea.
            //
            // Green open: breaking the opening low invalidates the original
            // bullish continuation idea.

            if (elapsed >= 1 &&
                elapsed <= ConfirmationBars &&
                !continuationTaken)
            {
                if (openingBearish && High[0] > openingHigh)
                    continuationInvalid = true;

                if (openingBullish && Low[0] < openingLow)
                    continuationInvalid = true;
            }

            // ---------------------------------------------------------------
            // Structure approximation
            // ---------------------------------------------------------------

            if (CurrentBar <= StructureLookback)
                return;

            double previousHigh = MAX(High, StructureLookback)[1];
            double previousLow = MIN(Low, StructureLookback)[1];

            bool bullishBOS = Close[0] > previousHigh;
            bool bearishBOS = Close[0] < previousLow;

            bool newBullishBOS =
                bullishBOS &&
                (double.IsNaN(lastBullishStructure) ||
                 Math.Abs(previousHigh - lastBullishStructure) > TickSize / 2.0);

            bool newBearishBOS =
                bearishBOS &&
                (double.IsNaN(lastBearishStructure) ||
                 Math.Abs(previousLow - lastBearishStructure) > TickSize / 2.0);

            if (newBullishBOS)
                lastBullishStructure = previousHigh;

            if (newBearishBOS)
                lastBearishStructure = previousLow;

            // ---------------------------------------------------------------
            // Displacement approximation
            // ---------------------------------------------------------------

            double range = High[0] - Low[0];
            double body = Math.Abs(Close[0] - Open[0]);

            double upperWick = High[0] - Math.Max(Open[0], Close[0]);
            double lowerWick = Math.Min(Open[0], Close[0]) - Low[0];

            double wickPercent =
                range > 0
                    ? ((upperWick + lowerWick) / range) * 100.0
                    : 100.0;

            double previousBody = Math.Abs(Close[1] - Open[1]);

            bool displacement =
                range > 0 &&
                body > previousBody * DisplacementMultiplier &&
                wickPercent <= MaxWickPercent;

            bool bullishDisplacement = displacement && Close[0] > Open[0];
            bool bearishDisplacement = displacement && Close[0] < Open[0];

            if (DebugVisuals)
            {
                // Only mark actual structural events. Avoid putting text on
                // every bar; that makes the Analyzer chart unreadable.
                if (newBullishBOS)
                    Draw.ArrowUp(this, "BOS_UP_" + CurrentBar, false, 0,
                        Low[0] - 3 * TickSize, Brushes.LimeGreen);

                if (newBearishBOS)
                    Draw.ArrowDown(this, "BOS_DN_" + CurrentBar, false, 0,
                        High[0] + 3 * TickSize, Brushes.Red);

                if (bullishDisplacement)
                    Draw.Dot(this, "DISP_UP_" + CurrentBar, false, 0,
                        Low[0] - 2 * TickSize, Brushes.LimeGreen);

                if (bearishDisplacement)
                    Draw.Dot(this, "DISP_DN_" + CurrentBar, false, 0,
                        High[0] + 2 * TickSize, Brushes.Red);

                if (elapsed >= 1 && elapsed <= ConfirmationBars && continuationInvalid)
                {
                    Draw.Text(this, "Invalid_" + CurrentBar, "CONT INVALID",
                        0, Low[0] - 5 * TickSize, Brushes.OrangeRed);
                }
            }

            // ---------------------------------------------------------------
            // PHASE 1: opening continuation
            // ---------------------------------------------------------------

            bool continuationPhase =
                elapsed > 0 &&
                elapsed < ContinuationMinutes;

            if (continuationPhase &&
                !continuationInvalid &&
                !continuationTaken &&
                tradeCount < MaxTradesPerSession &&
                Position.MarketPosition == MarketPosition.Flat)
            {
                if (openingBullish &&
                    (newBullishBOS || bullishDisplacement))
                {
                    EnterContinuationLong(newBullishBOS ? "BOS" : "DISPLACEMENT");
                    return;
                }

                if (openingBearish &&
                    (newBearishBOS || bearishDisplacement))
                {
                    EnterContinuationShort(newBearishBOS ? "BOS" : "DISPLACEMENT");
                    return;
                }
            }

            // ---------------------------------------------------------------
            // PHASE 2: mean reversion
            // ---------------------------------------------------------------

            bool reversionPhase =
                elapsed >= ContinuationMinutes &&
                elapsed < ReversionMinutes;

            if (!reversionPhase)
                return;

            if (tradeCount >= MaxTradesPerSession)
                return;

            bool canEnter =
                Position.MarketPosition == MarketPosition.Flat ||
                AllowLayering;

            if (!canEnter)
                return;

            // Above fair price -> short toward fair price.
            if (Close[0] > fairPrice)
            {
                double distanceToFair = Close[0] - fairPrice;

                if (distanceToFair < MinDistanceFromFair)
                    return;

                // If there is plenty of room, prioritize BOS.
                // If close to fair, displacement can be used instead.
                bool useBOS = newBearishBOS;

                bool useDisplacement =
                    bearishDisplacement &&
                    distanceToFair <= DisplacementOverrideDistance;

                if (useBOS || useDisplacement)
                {
                    EnterReversionShort(useBOS ? "BOS" : "DISPLACEMENT");
                    return;
                }
            }

            // Below fair price -> long toward fair price.
            if (Close[0] < fairPrice)
            {
                double distanceToFair = fairPrice - Close[0];

                if (distanceToFair < MinDistanceFromFair)
                    return;

                bool useBOS = newBullishBOS;

                bool useDisplacement =
                    bullishDisplacement &&
                    distanceToFair <= DisplacementOverrideDistance;

                if (useBOS || useDisplacement)
                {
                    EnterReversionLong(useBOS ? "BOS" : "DISPLACEMENT");
                    return;
                }
            }
        }

        // Position is not guaranteed to exist in DataLoaded. Initialize before
        // the first bar reaches any original trading logic or warmup guards.
        private void CsvInitializeLogger()
        {
            csvLogStage = "Initialize session iterator";
            if (BarsArray == null || BarsArray.Length == 0 || BarsArray[0] == null)
                throw new InvalidOperationException("Primary bars are unavailable for CSV initialization.");
            var initialPosition = Position;
            if (initialPosition == null)
                throw new InvalidOperationException("Strategy Position is unavailable on the first primary bar.");
            csvSessionIterator = new SessionIterator(BarsArray[0]);
            csvLogStage = "Read strategy parameters";
            var metadata = new Dictionary<string, object>();
            // Capture configured strategy properties without setting any of them.
            var parameters = new Dictionary<string, object>();
            foreach (var property in GetType().GetProperties())
                if (property.IsDefined(typeof(NinjaScriptPropertyAttribute), true) && property.CanRead)
                {
                    object value = property.GetValue(this, null);
                    parameters[property.Name] = value == null ? null : Convert.ToString(value, CultureInfo.InvariantCulture);
                }
            metadata["strategy_parameters"] = parameters;
            csvLogStage = "Read instrument and session metadata";
            metadata["strategy_name"] = Name;
            metadata["instrument"] = Instrument.FullName;
            metadata["tick_size"] = TickSize;
            metadata["point_value"] = Instrument.MasterInstrument.PointValue;
            metadata["currency"] = Instrument.MasterInstrument.Currency.ToString();
            metadata["bars_period"] = BarsPeriod.ToString();
            var tradingHours = BarsArray[0].TradingHours;
            metadata["trading_hours_template"] = CsvOptionalProperty(tradingHours, "Name");
            var sessionZone = tradingHours == null ? null : tradingHours.TimeZoneInfo;
            metadata["trading_hours_timezone"] = sessionZone == null ? null : sessionZone.Id;
            var runtime = new Dictionary<string, object>();
            foreach (string name in new[] { "Calculate", "EntriesPerDirection", "EntryHandling", "IsUnmanaged", "StopTargetHandling", "IsExitOnSessionCloseStrategy", "ExitOnSessionCloseSeconds", "BarsRequiredToTrade", "OrderFillResolution", "OrderFillResolutionType", "OrderFillResolutionValue", "Slippage", "IncludeCommission", "IsTickReplay", "StartBehavior" })
            {
                runtime[name] = CsvOptionalProperty(this, name);
            }
            runtime["Bars.IsTickReplay"] = CsvOptionalProperty(BarsArray[0], "IsTickReplay");
            metadata["runtime_settings"] = runtime;
            csvLogStage = "Validate initial strategy position";
            metadata["initial_strategy_quantity"] = initialPosition.Quantity;
            metadata["initial_strategy_market_position"] = initialPosition.MarketPosition.ToString();
            if (initialPosition.MarketPosition != MarketPosition.Flat)
                throw new InvalidOperationException("CSV accounting requires a flat initial strategy position.");
            string root = string.IsNullOrWhiteSpace(CsvLogOutputRoot)
                ? Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "ContRevBacktestLogs") : CsvLogOutputRoot;
            csvLogStage = "Create CSV output files";
            var options = NinjaTrader.Core.Globals.GeneralOptions;
            TimeZoneInfo sourceZone = options == null ? null : options.TimeZoneInfo;
            csvLogger = new ContRevCsvLogger(root, Name, Instrument.FullName,
                Instrument.MasterInstrument.PointValue, sourceZone,
                CsvCommissionMode, CsvCommissionPerContractPerSide, metadata);
            csvLogStage = "Initialization complete";
            try { Print("Cont & Rev CSV logging started: " + csvLogger.DirectoryPath); } catch { }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price,
            int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (!EnableCsvLogging || csvLoggingFailed) return;
            try
            {
                // Passed-by-value callback fields are the fill authority. Copy optional
                // reference fields once; never retain NinjaTrader Order/Execution objects.
                Order order = execution == null ? null : execution.Order;
                string action = order == null ? null : order.OrderAction.ToString();
                int sign = action == "Buy" || action == "BuyToCover" ? 1
                    : action == "Sell" || action == "SellShort" ? -1
                    : marketPosition == MarketPosition.Long ? 1 : marketPosition == MarketPosition.Short ? -1 : 0;
                var fill = new ContRevFill {
                    ExecutionId = executionId, OrderId = orderId, Price = price, Quantity = quantity, Time = time,
                    MarketPosition = marketPosition.ToString(), Sign = sign,
                    Side = action ?? (sign > 0 ? "Buy" : sign < 0 ? "Sell" : null),
                    OrderName = execution == null ? null : execution.Name,
                    EntrySignal = order == null ? null : order.FromEntrySignal,
                    Account = execution == null || execution.Account == null ? null : execution.Account.Name,
                    PlatformCommission = execution == null ? (double?)null : execution.Commission,
                    Phase = State.ToString(), Quality = order == null ? "OrderUnavailable;SideFromExecutionMarketPosition" : "Observed"
                };
                // Entry orders have no FromEntrySignal. Preserve their actual signal name.
                if (string.IsNullOrEmpty(fill.EntrySignal) &&
                    (fill.OrderName == "CONT_LONG" || fill.OrderName == "CONT_SHORT" || fill.OrderName == "REV_LONG" || fill.OrderName == "REV_SHORT"))
                    fill.EntrySignal = fill.OrderName;
                CsvLogSafely(delegate
                {
                    if (csvLogger != null) { fill.TradingDay = CsvTradingDay(time); csvLogStage = "Write execution"; csvLogger.Execution(fill); }
                });
            }
            catch (Exception ex) { CsvLogFailure(ex); }
        }

        protected override void OnMarketData(MarketDataEventArgs update)
        {
            if (!EnableCsvLogging || csvLoggingFailed || update.MarketDataType != MarketDataType.Last) return;
            DateTime time = update.Time;
            double price = update.Price;
            string phase = State.ToString();
            CsvLogSafely(delegate { if (csvLogger != null) { csvLogStage = "Write last-price observation"; csvLogger.Tick(time, CsvTradingDay(time), phase, price); } });
        }

        private string CsvTradingDay(DateTime time)
        {
            return csvSessionIterator.GetTradingDay(time).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        }

        private static string CsvOptionalProperty(object target, string name)
        {
            try
            {
                var property = target.GetType().GetProperty(name,
                    System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
                return property == null || !property.CanRead ? null
                    : Convert.ToString(property.GetValue(target, null), CultureInfo.InvariantCulture);
            }
            catch { return null; } // Optional metadata must not prevent execution logging.
        }

        private void CsvLogSafely(Action action)
        {
            lock (csvLogGate)
            {
                if (csvLoggingFailed) return;
                try { action(); } catch (Exception ex) { CsvLogFailure(ex); }
            }
        }

        private void CsvLogFailure(Exception error)
        {
            lock (csvLogGate)
            {
                if (csvLoggingFailed) return;
                csvLoggingFailed = true;
                try { if (csvLogger != null) csvLogger.Finish(error.ToString()); } catch { }
                // A failed logger must never throw into the order/strategy engine.
                try { Print("Cont & Rev CSV logging disabled at " + csvLogStage + " (" + State + "): " + error.ToString()); } catch { }
            }
        }

        // ---------------------------------------------------------------
        // Entries
        // ---------------------------------------------------------------

        private void EnterContinuationLong(string reason)
        {
            double stopPoints = GetDynamicStopPoints();
            double targetPoints = GetDynamicTargetPoints();

            SetStopLoss("CONT_LONG",
                CalculationMode.Ticks,
                PointsToTicks(stopPoints),
                false);

            SetProfitTarget("CONT_LONG",
                CalculationMode.Ticks,
                PointsToTicks(targetPoints));

            EnterLong(1, "CONT_LONG");
            continuationTaken = true;
            tradeCount++;
            debugTradeNumber++;
            activeEntryBar = CurrentBar;

            DrawDebugEntry("CONT LONG", reason, true);
        }

        private void EnterContinuationShort(string reason)
        {
            double stopPoints = GetDynamicStopPoints();
            double targetPoints = GetDynamicTargetPoints();

            SetStopLoss("CONT_SHORT",
                CalculationMode.Ticks,
                PointsToTicks(stopPoints),
                false);

            SetProfitTarget("CONT_SHORT",
                CalculationMode.Ticks,
                PointsToTicks(targetPoints));

            EnterShort(1, "CONT_SHORT");

            continuationTaken = true;
            tradeCount++;
            debugTradeNumber++;
            activeEntryBar = CurrentBar;

            DrawDebugEntry("CONT SHORT", reason, false);
        }

        private void EnterReversionLong(string reason)
        {
            double stopPoints = GetDynamicStopPoints();

            double targetPoints =
                ReversionTargetMode == ReversionTargetModeEnum.FairPrice
                    ? fairPrice - Close[0]
                    : GetDynamicTargetPoints();

            if (targetPoints <= 0)
                return;

            SetStopLoss("REV_LONG",
                CalculationMode.Ticks,
                PointsToTicks(stopPoints),
                false);

            SetProfitTarget("REV_LONG",
                CalculationMode.Ticks,
                PointsToTicks(targetPoints));

            EnterLong(1, "REV_LONG");

            tradeCount++;
            debugTradeNumber++;
            activeEntryBar = CurrentBar;

            DrawDebugEntry("REV LONG", reason, true);
        }

        private void EnterReversionShort(string reason)
        {
            double stopPoints = GetDynamicStopPoints();

            double targetPoints =
                ReversionTargetMode == ReversionTargetModeEnum.FairPrice
                    ? Close[0] - fairPrice
                    : GetDynamicTargetPoints();

            if (targetPoints <= 0)
                return;

            SetStopLoss("REV_SHORT",
                CalculationMode.Ticks,
                PointsToTicks(stopPoints),
                false);

            SetProfitTarget("REV_SHORT",
                CalculationMode.Ticks,
                PointsToTicks(targetPoints));

            EnterShort(1, "REV_SHORT");

            tradeCount++;
            debugTradeNumber++;
            activeEntryBar = CurrentBar;

            DrawDebugEntry("REV SHORT", reason, false);
        }
        private void DrawDebugSessionLevels()
        {
            if (!DebugVisuals || openingBarIndex < 0)
                return;

            int startBarsAgo = CurrentBar - openingBarIndex;

            if (startBarsAgo < 0)
                return;

            // Fair price: visible through the entire reversion window.
            Draw.Line(this, "FairPriceLine_" + openingBarIndex,
                false,
                startBarsAgo, fairPrice,
                0, fairPrice,
                Brushes.Goldenrod,
                DashStyleHelper.Dash,
                1);

            // Opening range: visible only during the continuation window.
            // After the continuation window expires, these lines stop updating.
            int continuationEndBarsAgo = Math.Max(
                0,
                CurrentBar - (openingBarIndex + ContinuationMinutes));

            if (CurrentBar <= openingBarIndex + ContinuationMinutes)
            {
                Draw.Line(this, "OpeningHighLine_" + openingBarIndex,
                    false,
                    startBarsAgo, openingHigh,
                    0, openingHigh,
                    Brushes.DodgerBlue,
                    DashStyleHelper.Solid,
                    1);

                Draw.Line(this, "OpeningLowLine_" + openingBarIndex,
                    false,
                    startBarsAgo, openingLow,
                    0, openingLow,
                    Brushes.DodgerBlue,
                    DashStyleHelper.Solid,
                    1);
            }
        }

        private void DrawDebugEntry(string setup, string reason, bool isLong)
        {
            if (!DebugVisuals)
                return;

            double y = isLong
                ? Low[0] - 8 * TickSize
                : High[0] + 8 * TickSize;

            string text =
                "#" + debugTradeNumber + " " + setup + " " + reason;

            if (isLong)
                Draw.ArrowUp(this, "ENTRY_" + CurrentBar, false, 0, y, Brushes.LimeGreen);
            else
                Draw.ArrowDown(this, "ENTRY_" + CurrentBar, false, 0, y, Brushes.Red);

            Draw.Text(this, "ENTRY_TXT_" + CurrentBar,
                text,
                0,
                isLong ? y - 4 * TickSize : y + 4 * TickSize,
                isLong ? Brushes.LimeGreen : Brushes.Red);
        }

        private double GetDynamicStopPoints()
        {
            double atr = ATR(14)[0];
            if (double.IsNaN(atr) || atr <= 0)
                return StopPoints;

            if (atr > 20.0)
                return 50.0;

            if (atr >= 7.0)
                return StopPoints;

            return 16.5;
        }

        private double GetDynamicTargetPoints()
        {
            double atr = ATR(14)[0];
            if (double.IsNaN(atr) || atr <= 0)
                return TargetPoints;

            if (atr > 20.0)
                return 75.0;

            if (atr >= 7.0)
                return TargetPoints;

            return 24.75;
        }

        private int PointsToTicks(double points)
        {
            return Math.Max(1, (int)Math.Round(points / TickSize));
        }

        // ---------------------------------------------------------------
        // Visual debugging
        //
        // DebugVisuals draws fair price, opening range, phase labels,
        // BOS/displacement markers, and entry reasons directly on the
        // Analyzer chart when chart rendering is available.
        //
        // Parameters
        // ---------------------------------------------------------------

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name = "Open Hour", Order = 1, GroupName = "Session")]
        public int OpenHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name = "Open Minute", Order = 2, GroupName = "Session")]
        public int OpenMinute { get; set; }

        [NinjaScriptProperty]
        [Range(1, 30)]
        [Display(Name = "Continuation Minutes", Order = 3, GroupName = "Session")]
        public int ContinuationMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(10, 180)]
        [Display(Name = "Reversion Minutes", Order = 4, GroupName = "Session")]
        public int ReversionMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(1, 3)]
        [Display(Name = "Opening Confirmation Bars", Order = 5, GroupName = "Session")]
        public int ConfirmationBars { get; set; }

        [NinjaScriptProperty]
        [Range(2, 50)]
        [Display(Name = "Structure Lookback", Order = 1, GroupName = "Structure")]
        public int StructureLookback { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name = "Displacement Multiplier", Order = 2, GroupName = "Structure")]
        public double DisplacementMultiplier { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Max Wick Percent", Order = 3, GroupName = "Structure")]
        public double MaxWickPercent { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 500.0)]
        [Display(Name = "Min Distance From Fair", Order = 4, GroupName = "Structure")]
        public double MinDistanceFromFair { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 500.0)]
        [Display(Name = "Displacement Override Distance", Order = 5, GroupName = "Structure")]
        public double DisplacementOverrideDistance { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 500.0)]
        [Display(Name = "Stop Points", Order = 1, GroupName = "Risk")]
        public double StopPoints { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 500.0)]
        [Display(Name = "Target Points", Order = 2, GroupName = "Risk")]
        public double TargetPoints { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Reversion Target", Order = 3, GroupName = "Risk")]
        public ReversionTargetModeEnum ReversionTargetMode { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Trades Per Session", Order = 1, GroupName = "Trade Filtering")]
        public int MaxTradesPerSession { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Layering", Order = 2, GroupName = "Trade Filtering")]
        public bool AllowLayering { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Debug Visuals", Order = 3, GroupName = "Trade Filtering")]
        public bool DebugVisuals { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable CSV Logging", Order = 1, GroupName = "CSV Logging")]
        public bool EnableCsvLogging { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output Root (blank = user data)", Order = 2, GroupName = "CSV Logging")]
        public string CsvLogOutputRoot { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Commission Mode", Order = 3, GroupName = "CSV Logging")]
        public ContRevCommissionMode CsvCommissionMode { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, double.MaxValue)]
        [Display(Name = "Commission Per Contract Per Side", Order = 4, GroupName = "CSV Logging")]
        public double CsvCommissionPerContractPerSide { get; set; }
    }

    public enum ReversionTargetModeEnum
    {
        FairPrice,
        FixedPoints
    }
}
