// VoltaBandBreakout.cs - NinjaTrader 8 strategy: Volta's noise-band breakout (F10 forward variant #43; F13 #2 by settings).
//
// STATUS: DRAFT, NEVER COMPILED OR RUN. Written on 15 Nov 2026 from the rules in strategy_lab.py (simulate_day / _run_trade)
// without access to NinjaTrader. Expect to fix small compile errors on the first import. SIM ACCOUNTS ONLY until it has
// matched Volta's own forward-test trades for at least 20 sessions (the frozen eval rule, knowledge/frozen/eval_rule.json).
// Never attach it to the funded account.
//
// What it does (plain words) - once per `CheckEveryMinutes` between 09:00 and 14:30 Chicago, while flat:
//   1. band   = today's 08:30 open  x  (1 +- BandMult x the average distance from the open at this minute over the
//               last 14 full sessions)
//   2. if the last closed 1-minute bar closed ABOVE the band -> buy at market; BELOW -> sell at market
//   3. stop   = 0.2 x the day's expected range (Volta's evening forecast, read from the repo once a day) x the open,
//               rounded to the tick, at least 8 ticks.   No forecast for today = NO TRADE (frozen rule).
//   4. target = TargetR x the stop distance.   Everything still open is closed at 14:59 Chicago.
//   5. F10: at most 3 trades a day, a new one only after a LOSING trade.  F13: at most 4, always re-enter.
//
// Settings for the two frozen variants:
//                       CheckEveryMinutes  BandMult  TargetR  MaxTradesPerDay  ReenterOnlyAfterLoss
//   F10 #43 (default)          60            1.2       5.0          3                 true
//   F13 #2                     15            1.2       2.0          4                 false
//
// Chart: MNQ (or NQ) 1-minute bars, at least 25 days loaded, any session template that contains 08:30-15:00 Chicago.
// Every decision is printed to the NinjaScript Output window and every closed trade is appended to
// Documents\NinjaTrader 8\volta_sim_trades.csv so it can be compared with Volta's own forward log.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class VoltaBandBreakout : Strategy
    {
        private const int SessionMinutes = 390;          // 08:30-15:00 Chicago
        private const int Lookback = 14;                 // sessions in the band average (frozen)
        private const int MinBarsFullSession = 370;      // a shorter day does not count as history
        private const int FirstCheck = 30;               // 09:00 = 30 minutes after 08:30
        private const int LastCheck = 360;               // 14:30
        private const int ExitMinute = 389;              // bar stamped 14:59 -> market exit fills at 14:59:00
        private const double StopShare = 0.2;            // share of the expected range (frozen)
        private const int MinStopTicks = 8;

        private TimeZoneInfo chicago;
        private readonly List<double[]> history = new List<double[]>();   // per past session: |close/open - 1| per minute 1..390
        private double[] todayClose;                     // close of the bar stamped 08:30 + m, m = 1..390 (index m)
        private int todayBars;
        private double todayOpen;
        private DateTime todayDate = DateTime.MinValue;
        private double fcFrac;                           // today's expected range as a fraction of price (0 = none -> no trade)
        private int entriesToday;
        private bool stopForToday;
        private int tradesSeen;
        private int stopTicksInUse;
        private DateTime fetchTriedFor = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Volta noise-band breakout (F10 #43 / F13 #2). DRAFT - SIM only.";
                Name = "VoltaBandBreakout";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 20;
                StartBehavior = StartBehavior.WaitUntilFlat;

                CheckEveryMinutes = 60;
                BandMult = 1.2;
                TargetR = 5.0;
                MaxTradesPerDay = 3;
                ReenterOnlyAfterLoss = true;
                Quantity = 1;
                TradeHistoricalBars = false;
                ManualFcFrac = 0.0;
                InputsUrl = "https://raw.githubusercontent.com/vannaflow1/nasdaq-bot/main/knowledge/sim_inputs.json";
            }
            else if (State == State.Configure)
            {
                chicago = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
            }
        }

        // Bar time (NinjaTrader stamps a bar with its CLOSE time, in the platform's time zone) -> Chicago clock.
        private DateTime ChicagoTime(DateTime barTime)
        {
            return TimeZoneInfo.ConvertTime(DateTime.SpecifyKind(barTime, DateTimeKind.Unspecified),
                                            Core.Globals.GeneralOptions.TimeZoneInfo, chicago);
        }

        protected override void OnBarUpdate()
        {
            if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
            {
                if (CurrentBar == 0) Print("VoltaBandBreakout needs a 1-minute chart - doing nothing.");
                return;
            }

            DateTime ct = ChicagoTime(Time[0]);
            int m = ct.Hour * 60 + ct.Minute - 510;      // minutes after 08:30; the 08:30-08:31 bar is stamped m = 1
            if (m < 1 || m > SessionMinutes) return;      // outside the regular session: ignore

            if (ct.Date != todayDate) StartNewDay(ct.Date);
            if (m == 1) todayOpen = Open[0];
            if (todayOpen == 0) return;                   // the day's first bar was missing: no open, no trades today
            todayClose[m] = Close[0];
            todayBars++;

            // bookkeeping of closed trades (re-entry rule + CSV log)
            if (SystemPerformance.AllTrades.Count > tradesSeen)
            {
                for (int i = tradesSeen; i < SystemPerformance.AllTrades.Count; i++) LogTrade(SystemPerformance.AllTrades[i]);
                Trade last = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                tradesSeen = SystemPerformance.AllTrades.Count;
                if (ReenterOnlyAfterLoss && last.ProfitCurrency > 0) stopForToday = true;   // F10: a winner ends the day
            }

            // time exit: the bar stamped 14:59 has closed -> flatten (fills at the 14:59:00 open)
            if (m >= ExitMinute)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("VoltaTimeExit", "VoltaLong");
                else if (Position.MarketPosition == MarketPosition.Short) ExitShort("VoltaTimeExit", "VoltaShort");
                return;
            }

            if (State == State.Historical && !TradeHistoricalBars) return;   // history only feeds the band average
            if (m < FirstCheck || m > LastCheck || (m - FirstCheck) % CheckEveryMinutes != 0) return;
            if (Position.MarketPosition != MarketPosition.Flat || stopForToday || entriesToday >= MaxTradesPerDay) return;
            if (history.Count < Lookback) { Print(ct + "  no check: only " + history.Count + " full sessions of history (need " + Lookback + ")"); return; }
            if (fcFrac <= 0 && ManualFcFrac <= 0 && State == State.Realtime && fetchTriedFor != todayDate)
            {
                fetchTriedFor = todayDate;                // one download per day, at the first check that needs it
                fcFrac = FetchFcFrac(todayDate);
            }
            if (fcFrac <= 0) { Print(ct + "  no trade today: no range forecast for " + todayDate.ToString("yyyy-MM-dd")); return; }

            double sigma = 0; int n = 0;
            foreach (double[] h in history) { if (!double.IsNaN(h[m])) { sigma += h[m]; n++; } }
            if (n == 0) return;
            sigma /= n;
            if (sigma <= 0) return;
            double up = todayOpen * (1 + BandMult * sigma), dn = todayOpen * (1 - BandMult * sigma);
            int side = Close[0] > up ? 1 : (Close[0] < dn ? -1 : 0);
            Print(string.Format(CultureInfo.InvariantCulture, "{0:HH:mm} CT check: close {1:F2}, band {2:F2} .. {3:F2} -> {4}",
                                ct, Close[0], dn, up, side == 1 ? "LONG" : side == -1 ? "SHORT" : "inside, no trade"));
            if (side == 0) return;

            int stopTicks = Math.Max((int)Math.Round(StopShare * fcFrac * todayOpen / TickSize), MinStopTicks);
            int targetTicks = (int)Math.Round(TargetR * stopTicks);
            stopTicksInUse = stopTicks;
            string name = side == 1 ? "VoltaLong" : "VoltaShort";
            SetStopLoss(name, CalculationMode.Ticks, stopTicks, false);
            SetProfitTarget(name, CalculationMode.Ticks, targetTicks);
            if (side == 1) EnterLong(Quantity, name); else EnterShort(Quantity, name);
            entriesToday++;
            Print(string.Format(CultureInfo.InvariantCulture, "   entry #{0} {1}: stop {2} ticks ({3:F2} pts), target {4} ticks",
                                entriesToday, name, stopTicks, stopTicks * TickSize, targetTicks));
        }

        private void StartNewDay(DateTime date)
        {
            // store yesterday if it was a full session
            if (todayClose != null && todayOpen > 0 && todayBars >= MinBarsFullSession)
            {
                double[] dist = new double[SessionMinutes + 1];
                double lastClose = double.NaN;
                for (int k = 1; k <= SessionMinutes; k++)
                {
                    if (!double.IsNaN(todayClose[k])) lastClose = todayClose[k];             // carry the last close over a missing minute
                    dist[k] = double.IsNaN(lastClose) ? double.NaN : Math.Abs(lastClose / todayOpen - 1.0);
                }
                history.Add(dist);
                if (history.Count > Lookback) history.RemoveAt(0);
            }
            todayDate = date;
            todayClose = new double[SessionMinutes + 1];
            for (int k = 0; k <= SessionMinutes; k++) todayClose[k] = double.NaN;
            todayBars = 0; todayOpen = 0; entriesToday = 0; stopForToday = false;
            fcFrac = ManualFcFrac > 0 ? ManualFcFrac : 0.0;   // otherwise downloaded at the first check of the day (see OnBarUpdate)
        }

        // Reads {"session": "YYYY-MM-DD", "fc_frac": 0.0157, ...} published by tools/sim_inputs.py. Wrong date = 0 = no trade.
        private double FetchFcFrac(DateTime date)
        {
            try
            {
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
                string txt;
                using (WebClient wc = new WebClient()) txt = wc.DownloadString(InputsUrl + "?t=" + DateTime.UtcNow.Ticks);
                Match s = Regex.Match(txt, "\"session\"\\s*:\\s*\"(\\d{4}-\\d{2}-\\d{2})\"");
                Match f = Regex.Match(txt, "\"fc_frac\"\\s*:\\s*([0-9.eE+-]+)");
                if (!s.Success || !f.Success) { Print("Volta inputs: file not understood - no trades today."); return 0; }
                if (s.Groups[1].Value != date.ToString("yyyy-MM-dd"))
                {
                    Print("Volta inputs are for " + s.Groups[1].Value + ", today is " + date.ToString("yyyy-MM-dd") + " - no trades today.");
                    return 0;
                }
                double v = double.Parse(f.Groups[1].Value, CultureInfo.InvariantCulture);
                if (v < 0.002 || v > 0.15) { Print("Volta inputs: fc_frac " + v + " looks wrong - no trades today."); return 0; }
                Print("Volta inputs for " + s.Groups[1].Value + ": expected range " + (v * 100).ToString("F2", CultureInfo.InvariantCulture) + "% of price.");
                return v;
            }
            catch (Exception e)
            {
                Print("Volta inputs could not be loaded (" + e.Message + ") - no trades today.");
                return 0;
            }
        }

        private void LogTrade(Trade t)
        {
            try
            {
                string path = Path.Combine(Core.Globals.UserDataDir, "volta_sim_trades.csv");
                if (!File.Exists(path)) File.AppendAllText(path, "entry_time_chicago,exit_time_chicago,side,entry,exit,stop_ticks,pnl_points,R\r\n");
                double pts = (t.Exit.Price - t.Entry.Price) * (t.Entry.MarketPosition == MarketPosition.Long ? 1 : -1);
                double r = stopTicksInUse > 0 ? pts / (stopTicksInUse * TickSize) : 0;
                File.AppendAllText(path, string.Format(CultureInfo.InvariantCulture, "{0:yyyy-MM-dd HH:mm},{1:yyyy-MM-dd HH:mm},{2},{3:F2},{4:F2},{5},{6:F2},{7:F2}\r\n",
                    ChicagoTime(t.Entry.Time), ChicagoTime(t.Exit.Time), t.Entry.MarketPosition == MarketPosition.Long ? "LONG" : "SHORT",
                    t.Entry.Price, t.Exit.Price, stopTicksInUse, pts, r));
            }
            catch (Exception e) { Print("trade log failed: " + e.Message); }
        }

        #region Settings
        [NinjaScriptProperty, Range(5, 120)]
        [Display(Name = "Check every (minutes)", Description = "F10: 60, F13: 15", Order = 1, GroupName = "Volta")]
        public int CheckEveryMinutes { get; set; }

        [NinjaScriptProperty, Range(0.1, 3.0)]
        [Display(Name = "Band multiplier", Description = "1.2 for both frozen variants", Order = 2, GroupName = "Volta")]
        public double BandMult { get; set; }

        [NinjaScriptProperty, Range(0.5, 10.0)]
        [Display(Name = "Target (R)", Description = "F10: 5, F13: 2", Order = 3, GroupName = "Volta")]
        public double TargetR { get; set; }

        [NinjaScriptProperty, Range(1, 10)]
        [Display(Name = "Max trades per day", Description = "F10: 3, F13: 4", Order = 4, GroupName = "Volta")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Re-enter only after a loss", Description = "F10: yes, F13: no", Order = 5, GroupName = "Volta")]
        public bool ReenterOnlyAfterLoss { get; set; }

        [NinjaScriptProperty, Range(1, 20)]
        [Display(Name = "Contracts", Order = 6, GroupName = "Volta")]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Trade on historical bars", Description = "Leave off. History is only used for the band average.", Order = 7, GroupName = "Volta")]
        public bool TradeHistoricalBars { get; set; }

        [NinjaScriptProperty, Range(0.0, 0.15)]
        [Display(Name = "Manual expected range (0 = read from Volta)", Description = "Only for testing, e.g. 0.0158", Order = 8, GroupName = "Volta")]
        public double ManualFcFrac { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Volta inputs URL", Order = 9, GroupName = "Volta")]
        public string InputsUrl { get; set; }
        #endregion
    }
}
