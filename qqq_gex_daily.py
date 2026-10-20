"""
qqq_gex_daily.py  -  daily QQQ dealer-gamma (GEX) reading + paper-trade logger.

Run once per trading day AFTER 22:20 Luxembourg time (16:20 New York), so the
CBOE delayed chain reflects the close:

    python qqq_gex_daily.py

What it does
 1. Downloads the free CBOE delayed QQQ option chain (bid/ask, OI, gamma).
 2. Computes spot by put-call parity and net GEX exactly as in the 2011-2025
    backtest (gex.py), and ranks today's value against the trailing 252 days.
 3. Tells you what that historically meant for TOMORROW's volatility.
 4. If rank >= 0.80 it logs a PAPER iron fly (ATM straddle sold, wings +-3%,
    next expiry) to paper_trades.csv, priced at both mid and natural (bid/ask).
    It also settles earlier paper trades whose expiry has passed.

THIS IS A PAPER-TRADING TOOL. The backtest edge is real for volatility but
the tradeable fly is NOT proven (positive 2019-2025 only, borderline on the
concentration check). Log at least 40 paper trades before any real money.

Files it keeps next to itself:
  gex_history.csv   - date, gexn (seeded with 2011-2025 history; appends daily)
  paper_trades.csv  - paper fly log
Note: history ends 2025-12-15, so for the first ~60 trading days the rank
compares today against stale 2025 values. Treat signals as unreliable until
gex_history.csv has ~3 months of live rows.
"""
import json, os, sys, math, urllib.request, urllib.error
from datetime import datetime, date
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "gex_history.csv")
PAPER = os.path.join(HERE, "paper_trades.csv")
URL = "https://cdn-api.cboe.com/api/global/delayed_quotes/options/QQQ.json"
WING = 0.03
THRESH = 0.80
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")   # set as a GitHub secret - never in the public code
NTFY_URL = "https://ntfy.sh/" + NTFY_TOPIC

import io
_LOG = io.StringIO()
_print = print
def print(*a, **k):                      # noqa: A001 - tee everything into the push message
    _print(*a, **k)
    if k.get("file") is None:
        _LOG.write(" ".join(str(x) for x in a) + "\n")


DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")   # GitHub secret - posts go to the Discord channel
_COLORS = {"urgent": 0xE03131, "high": 0xF08C00, "default": 0x1C7ED6, "low": 0x868E96}
_EMOJI = {"rotating_light": "🚨", "chart_with_upwards_trend": "📈", "newspaper": "📰", "sunrise": "🌅",
          "crystal_ball": "🔮", "bar_chart": "📊", "warning": "⚠️", "white_check_mark": "✅", "wastebasket": "🗑️", "brain": "🧠", "notebook": "📓", "nerd": "🤓", "books": "📚", "bulb": "💡"}


def _discord(title, body, priority, tags, hook=None):
    import time
    emoji = _EMOJI.get(tags.split(",")[0].strip(), "") if tags else ""
    body = body or "(empty)"
    parts = [body[i:i + 4000] for i in range(0, len(body), 4000)] or [""]
    for n, part in enumerate(parts):
        embed = {"title": (f"{emoji} {title}".strip() if n == 0 else f"{title} (cont.)")[:256],
                 "description": part, "color": _COLORS.get(priority, _COLORS["default"])}
        data = json.dumps({"username": "Volta", "embeds": [embed],
                           "allowed_mentions": {"parse": []}}).encode("utf-8")
        req = urllib.request.Request(hook or DISCORD_WEBHOOK, data=data, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "DiscordBot (https://github.com/vannaflow1/nasdaq-bot, 1.0)"})
        for attempt in range(3):
            try:
                urllib.request.urlopen(req, timeout=30).read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:                      # rate limited: wait and retry
                    time.sleep(2 + attempt * 2)
                    continue
                raise
        time.sleep(1)


def push(title, body, priority="default", tags="", hook=None):
    try:
        if hook or DISCORD_WEBHOOK:
            _discord(title, body, priority, tags, hook)
        elif NTFY_TOPIC:
            req = urllib.request.Request(NTFY_URL, data=body.encode("utf-8"), method="POST",
                                         headers={"Title": title, "Priority": priority, "Tags": tags})
            urllib.request.urlopen(req, timeout=30).read()
        else:
            _print("[no DISCORD_WEBHOOK / NTFY_TOPIC set - would push]", title)
    except Exception as e:                # never let the notifier crash the script
        _print("push failed:", e)

# historical next-day outcome by GEX quintile, 2022-2025 holdout (gex_test.py)
QUINTILE_NOTE = {
    1: "LOW gamma  - next day historically WILDEST (avg realized vol ~19.6%, RV/IV 0.80)",
    2: "low-mid    - next day avg realized vol ~18.6%",
    3: "middle     - next day avg realized vol ~16.0%",
    4: "high-mid   - next day avg realized vol ~13.3%",
    5: "HIGH gamma - next day historically CALMEST (avg realized vol ~11.2%, RV/IV 0.60)",
}


def load_chain(path=None):
    if path:
        raw = json.load(open(path))
    else:
        print("downloading CBOE QQQ chain (can take a minute on a slow connection)...", flush=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0",
                                                   "Accept-Encoding": "gzip"})
        resp = urllib.request.urlopen(req, timeout=120)
        body = resp.read()
        if resp.headers.get("Content-Encoding", "") == "gzip" or body[:2] == b"\x1f\x8b":
            import gzip
            body = gzip.decompress(body)
        print(f"  got {len(body)/1e6:.1f} MB", flush=True)
        raw = json.loads(body)
    rows = raw["data"]["options"]
    d = pd.DataFrame(rows)
    # data date = date of the latest trade in the chain (NY time), so a run on
    # Saturday still files Friday's close under Friday
    if "last_trade_time" in d:
        ltt = pd.to_datetime(d["last_trade_time"], errors="coerce").dropna()
        ts = ltt.max().normalize() if len(ltt) else pd.Timestamp(raw["timestamp"][:10])
    else:
        ts = pd.Timestamp(raw.get("timestamp", datetime.now().isoformat())[:10])
    sym = d["option"].str.extract(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")
    d["expiration"] = pd.to_datetime(sym[1], format="%y%m%d")
    d["is_call"] = sym[2] == "C"
    d["strike"] = sym[3].astype(float) / 1000.0
    d = d[sym[0] == "QQQ"].copy()
    for c in ["bid", "ask", "open_interest", "gamma", "iv", "delta"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    d["date"] = ts
    d["dte"] = (d["expiration"] - ts).dt.days
    d["mid"] = (d.bid + d.ask) / 2
    return ts, d


def spot_by_parity(d):
    x = d[(d.dte >= 1) & (d.dte <= 45) & (d.bid > 0) & (d.ask > 0)]
    x = x[x.dte == x.dte.min()]
    c = x[x.is_call].set_index("strike").mid
    p = x[~x.is_call].set_index("strike").mid
    cp = pd.concat([c.rename("c"), p.rename("p")], axis=1).dropna()
    k = (cp.c - cp.p).abs().idxmin()
    return float(k + cp.at[k, "c"] - cp.at[k, "p"])


def gexn(d, S):
    x = d[(d.open_interest > 0) & (d.dte >= 0)]
    sign = np.where(x.is_call, 1.0, -1.0)
    gex = (sign * x.gamma * x.open_interest * 100 * S * S * 0.01).sum()
    return gex / (x.open_interest.sum() * 100 * S) * 1e4


def gamma_sanity(d, S):
    """Check CBOE gamma uses the same convention as the backtest data."""
    sys.path.insert(0, HERE)
    try:
        import greeks
    except ImportError:
        return None
    x = d[(d.dte >= 5) & (d.dte <= 60) & (d.iv > 0.05) & (d.gamma > 0)
          & (d.delta.abs().between(0.3, 0.7))]
    if len(x) < 10:
        return None
    g = greeks.gamma(S, x.strike.values, x.dte.values / 365.0, 0.04, x.iv.values)
    return float(np.median(x.gamma.values / g))


def build_fly(d, S):
    x = d[(d.dte >= 1) & (d.dte <= 4) & (d.bid > 0) & (d.ask > d.bid)]
    if x.empty:
        return None
    x = x[x.dte == x.dte.min()]
    c = x[x.is_call].set_index("strike")
    p = x[~x.is_call].set_index("strike")
    common = c.index.intersection(p.index)
    ks = common[np.abs(common - S).argmin()]
    kc = c.index[np.abs(c.index - (ks + WING * S)).argmin()]
    kp = p.index[np.abs(p.index - (ks - WING * S)).argmin()]
    if kc <= ks or kp >= ks:
        return None
    mid = c.at[ks, "mid"] + p.at[ks, "mid"] - c.at[kc, "mid"] - p.at[kp, "mid"]
    nat = c.at[ks, "bid"] + p.at[ks, "bid"] - c.at[kc, "ask"] - p.at[kp, "ask"]
    width = max(kc - ks, ks - kp)
    return dict(expiration=str(x.expiration.iat[0].date()), short=ks, call_wing=kc,
                put_wing=kp, credit_mid=round(mid, 2), credit_natural=round(nat, 2),
                max_risk_per_lot=round((width - nat) * 100, 0))


def settle(ts, S):
    if not os.path.exists(PAPER):
        return
    t = pd.read_csv(PAPER)
    if "pnl_natural" not in t:
        t["settle_spot"] = np.nan; t["pnl_mid"] = np.nan; t["pnl_natural"] = np.nan
    due = t.pnl_natural.isna() & (pd.to_datetime(t.expiration) <= ts)
    for i in t.index[due]:
        r = t.loc[i]
        pay = (abs(S - r.short) - max(S - r.call_wing, 0) - max(r.put_wing - S, 0))
        t.loc[i, "settle_spot"] = round(S, 2)
        t.loc[i, "settle_exact"] = pd.Timestamp(r.expiration) == ts
        t.loc[i, "pnl_mid"] = round((r.credit_mid - pay) * 100 - 2.6, 0)
        t.loc[i, "pnl_natural"] = round((r.credit_natural - pay) * 100 - 2.6, 0)
        print(f"  settled paper fly from {r.signal_date}: natural P&L ${t.loc[i,'pnl_natural']:.0f}"
              + ("" if t.loc[i, "settle_exact"] else "  (APPROX: not run on expiry day)"))
    t.to_csv(PAPER, index=False)
    done = t.dropna(subset=["pnl_natural"])
    if len(done):
        print(f"  paper record: {len(done)} trades, total ${done.pnl_natural.sum():.0f}, "
              f"avg ${done.pnl_natural.mean():.1f}, win {100*(done.pnl_natural>0).mean():.0f}%")


def market_open_now():
    """True during US regular hours (+15 min CBOE delay): chain is intraday, not a close."""
    try:
        from zoneinfo import ZoneInfo
        ny = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return False
    mins = ny.hour * 60 + ny.minute
    return ny.weekday() < 5 and 9 * 60 + 30 <= mins < 16 * 60 + 20


def main():
    if len(sys.argv) == 1 and market_open_now():
        print("US market is open (or <20 min after close) - chain is intraday, not a close.")
        print("Skipped so the history isn't polluted. It will run again tonight.")
        return
    ts, d = load_chain(sys.argv[1] if len(sys.argv) > 1 else None)
    S = spot_by_parity(d)
    g = gexn(d, S)
    ratio = gamma_sanity(d, S)

    h = pd.read_csv(HIST, parse_dates=["date"]) if os.path.exists(HIST) else pd.DataFrame(columns=["date", "gexn"])
    h = h[h.date != ts]
    past = h.sort_values("date").gexn.tail(252).to_numpy(float)
    rank = float((g > past).mean()) if len(past) >= 126 else float("nan")
    h = pd.concat([h, pd.DataFrame({"date": [ts], "gexn": [round(g, 4)]})]).sort_values("date")
    h.to_csv(HIST, index=False, date_format="%Y-%m-%d")
    live_rows = int((h.date > "2025-12-15").sum())

    q = min(5, int(rank * 5) + 1) if not math.isnan(rank) else None
    print(f"\nQQQ GEX  {ts.date()}   spot {S:.2f}")
    print(f"  net GEX (normalised) {g:.1f}   rank vs last 252 days: {rank:.2f}   quintile {q}")
    if q:
        print(f"  -> {QUINTILE_NOTE[q]}")
    if ratio is not None and not (0.8 < ratio < 1.25):
        print(f"  !! CBOE gamma / Black-Scholes gamma = {ratio:.2f} - convention differs from the backtest, rank NOT comparable")
    if live_rows < 60:
        print(f"  !! only {live_rows} live days in history - rank still leans on stale 2025 data")

    settle(ts, S)

    if not math.isnan(rank) and rank >= THRESH:
        fly = build_fly(d, S)
        if fly:
            fly = dict(signal_date=str(ts.date()), spot=round(S, 2), gex_rank=round(rank, 3), **fly)
            print(f"  PAPER SIGNAL: sell {fly['short']} straddle, buy {fly['put_wing']}P / {fly['call_wing']}C, "
                  f"exp {fly['expiration']}  credit mid {fly['credit_mid']} / natural {fly['credit_natural']}  "
                  f"max risk ${fly['max_risk_per_lot']:.0f}/lot")
            t = pd.read_csv(PAPER) if os.path.exists(PAPER) else pd.DataFrame()
            if t.empty or not (t.signal_date == fly["signal_date"]).any():
                pd.concat([t, pd.DataFrame([fly])]).to_csv(PAPER, index=False)
    else:
        print("  no paper trade today (needs rank >= 0.80)")


if __name__ == "__main__":
    try:
        main()
        msg = _LOG.getvalue()
        lines = [l for l in msg.splitlines() if not l.startswith(("downloading", "  got "))]
        hi = "PAPER SIGNAL" in msg
        lo = "LOW gamma" in msg
        if "Skipped" in msg:
            title = "QQQ GEX: skipped (market open)"
        else:
          title = ("QQQ GEX: HIGH gamma - calm expected, paper fly logged" if hi else
                 "QQQ GEX: LOW gamma - wild day risk, size down" if lo else
                 "QQQ GEX: normal day")
        push(title, "\n".join(lines).strip(), priority="high" if (hi or lo) else "default",
             tags="chart_with_upwards_trend")
    except Exception as e:
        import traceback
        push("QQQ GEX bot ERROR", traceback.format_exc()[-1500:], priority="high", tags="warning")
        raise
