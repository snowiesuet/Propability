using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading.Tasks;
using NinjaTrader.NinjaScript.Strategies;

internal static class LoggerHarness
{
    private static readonly DateTime Start = new DateTime(2026, 10, 21, 18, 0, 0);
    private static ContRevCsvLogger New(string root, string name, ContRevCommissionMode mode, double rate)
    {
        return new ContRevCsvLogger(Path.Combine(root, name), "Cont, Rev\n\"test\"", "NQ 12-26", 20,
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"), mode, rate, new Dictionary<string, object>());
    }
    private static ContRevFill Fill(string id, int sign, int quantity, double price, string signal, int minute)
    {
        return new ContRevFill { ExecutionId = id, OrderId = "order_" + id, OrderName = sign > 0 ? "Buy" : "Sell",
            Account = "Test", MarketPosition = sign > 0 ? "Long" : "Short", Side = sign > 0 ? "Buy" : "Sell",
            Sign = sign, Quantity = quantity, Price = price, EntrySignal = signal, Time = Start.AddMinutes(minute),
            TradingDay = "2026-10-22", Phase = "Historical" };
    }
    public static void Main(string[] args)
    {
        CultureInfo.CurrentCulture = new CultureInfo("de-DE");
        string root = args[0]; Directory.CreateDirectory(root);
        var main = New(root, "main", ContRevCommissionMode.FixedPerContractPerSide, 0.5);
        main.Bar(Start, "2026-10-22", "Historical", 100, 105, 90, 100, 1234);
        main.Execution(Fill("a", 1, 3, 100, "A", 1));
        main.Tick(Start.AddMinutes(1).AddSeconds(1), "2026-10-22", "Historical", 115);
        main.Execution(Fill("b", 1, 2, 110, "B", 2));
        main.Execution(Fill("c", -1, 1, 120, "B", 3));
        main.Execution(Fill("c", -1, 1, 120, "B", 3)); // reliable duplicate
        main.Execution(Fill("d", -1, 3, 90, null, 4));
        main.Execution(Fill("e", -1, 3, 105, null, 5)); // closes one and opens short two
        main.Execution(Fill("f", 1, 1, 95, null, 6));
        main.Execution(Fill("g", 1, 1, 100, null, 7));
        main.Finish(null); main.Finish(null);

        var unknown = New(root, "unknown", ContRevCommissionMode.Unknown, 0);
        unknown.Execution(Fill("a", -1, 2, 100, "A", 0));
        unknown.Execution(Fill("b", 1, 1, 90, null, 1));
        unknown.Finish(null); // keep one open, unknown net costs

        var platform = New(root, "platform", ContRevCommissionMode.Platform, 99);
        var p1 = Fill("a", 1, 1, 100, "A", 0); p1.PlatformCommission = 0; platform.Execution(p1);
        var p2 = Fill("b", -1, 1, 102, null, 1); p2.PlatformCommission = 2; platform.Execution(p2);
        platform.Finish(null);

        var partials = New(root, "partials", ContRevCommissionMode.FixedPerContractPerSide, 0.25);
        var a1 = Fill("a1", 1, 2, 100, "A", 0); a1.OrderId = "entry"; partials.Execution(a1);
        var a2 = Fill("a2", 1, 1, 110, "A", 0); a2.OrderId = "entry"; partials.Execution(a2);
        var x1 = Fill("x1", -1, 1, 120, "A", 1); x1.OrderName = "Stop loss"; partials.Execution(x1);
        var x2 = Fill("x2", -1, 2, 90, null, 2); x2.OrderName = "Exit on session close";
        x2.Quality = "OrderUnavailable;SideFromExecutionMarketPosition"; partials.Execution(x2);
        partials.Finish(null);

        var missingCost = New(root, "missing_platform_cost", ContRevCommissionMode.Platform, 0);
        missingCost.Execution(Fill("a", 1, 1, 100, "A", 0)); missingCost.Finish(null);

        var identity = New(root, "identity", ContRevCommissionMode.FixedPerContractPerSide, 0);
        var i1 = Fill(null, 1, 1, 100, "A", 0); i1.Quality = "OrderUnavailable;SideFromExecutionMarketPosition";
        identity.Execution(i1); identity.Execution(Fill(null, 1, 1, 100, "A", 0));
        identity.Execution(Fill("same", -1, 1, 101, null, 0));
        var i2 = Fill("same", -1, 1, 102, null, 0); i2.Phase = "Realtime"; identity.Execution(i2);
        identity.Finish(null);

        var invalid = New(root, "unresolved", ContRevCommissionMode.Unknown, 0);
        var bad = Fill("a", 0, 1, 100, null, 0); bad.Side = null; invalid.Execution(bad);
        invalid.Execution(Fill("b", 1, 1, 100, "A", 1)); invalid.Finish(null);

        var dst = New(root, "dst", ContRevCommissionMode.FixedPerContractPerSide, 0);
        dst.Tick(new DateTime(2026, 11, 1, 1, 30, 0), "2026-11-02", "Realtime", 100);
        dst.Tick(new DateTime(2026, 3, 8, 2, 30, 0), "2026-03-09", "Realtime", 100);
        dst.Finish(null);

        var failed = New(root, "failed", ContRevCommissionMode.Unknown, 0);
        failed.Finish("Simulated write failure");
        Parallel.For(0, 4, x => { var concurrent = New(root, "concurrent", ContRevCommissionMode.Unknown, 0); concurrent.Finish(null); });
        var fallback = New(root, "fallback", ContRevCommissionMode.FixedPerContractPerSide, 0);
        fallback.Execution(Fill("a", 1, 1, 100, "A", 0));
        fallback.Execution(Fill("b", -1, 1, 101, "Missing", 1)); fallback.Finish(null);

        // File sharing conflict exercises actual IO failure; adapter uses Finish(error).
        var io = New(root, "io", ContRevCommissionMode.Unknown, 0);
        try
        {
            using (var locked = new FileStream(Path.Combine(io.DirectoryPath, "run_metadata.json.tmp"), FileMode.Create, FileAccess.Write, FileShare.None))
                io.Finish(null);
            throw new Exception("Expected metadata IO failure");
        }
        catch (IOException) { }
        Console.WriteLine("Fixtures written to " + root);
    }
}
