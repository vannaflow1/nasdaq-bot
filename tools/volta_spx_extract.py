"""Volta - SPX options extractor. Runs on your PC, reads every day of the Parquet folder and writes small summary files
to the folder volta_out next to it. Nothing is deleted or changed in your data.

What it keeps (every day 2019 -> 2026):
  contracts_YYYY.parquet  one row per day x option (0-7 days to expiry, strikes within 10% of SPX): open interest,
                          volume, BUY vs SELL volume (trade price vs bid/ask), premium bought/sold, and the option's
                          mid price at 9 moments of the day + SPX at those moments (greeks/IV are computed later)
  minutes_YYYY.parquet    one row per day x minute: SPX, VIX, VVIX, and buy/sell flow split by expiry
                          (0DTE / 1-2 days / 3-7 days) x calls/puts x moneyness bucket; ATM straddle and wing prices
Run it again any time: years that are already finished are skipped.
"""
import glob, os, sys, time
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Parquet") if os.path.isdir(os.path.join(ROOT, "Parquet")) else ROOT
OUT = os.path.join(ROOT, "volta_out")
SNAPS = ["09:35", "10:00", "10:30", "11:00", "12:00", "13:00", "14:00", "15:00", "15:50"]
WINDOW = 0.10                       # keep strikes within +-10% of SPX
FILES = {"tq": ("quote trade tick", "SPXW_trade_quote_tick_maxdte7_"), "q": ("Quote 1min", "SPXW_quotes_1m_maxdte7_"),
         "oi": ("oi", "SPXW_oi_maxdte7_"), "spx": ("ohlc tick", "SPX_ohlc_tick_"), "vix": ("vix", "VIX_tick_"),
         "vvix": ("vvix", "VVIX_tick_")}


def read(kind, day):
    folder, prefix = FILES[kind]
    p = os.path.join(SRC, folder, f"{prefix}{day}.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else None


def minute_series(df, col="price"):
    """last tick of each minute, labelled by the minute it closes (09:31 = 09:30:00-09:30:59)."""
    if df is None or df.empty: return None
    t = pd.to_datetime(df["timestamp"])
    s = pd.Series(df[col].values, index=t).sort_index()
    s = s[s > 0]
    return s.resample("1min", label="right", closed="left").last().ffill()


def dte_bucket(dte):
    return np.where(dte <= 0, "d0", np.where(dte <= 2, "d12", "d37"))


def money_bucket(strike, spx, right):
    m = (strike / spx - 1) * np.where(right == "CALL", 1, -1)     # + = out of the money for both calls and puts
    return np.select([m < -0.005, m <= 0.005, m <= 0.015], ["itm", "atm", "otm1"], "otm2")


def one_day(day):
    d0 = pd.Timestamp(day)
    spx = minute_series(read("spx", day))
    if spx is None: return None, None
    spx = spx.between_time("09:31", "16:00")
    if len(spx) < 300: return None, None
    spx_open = float(spx.iloc[0])
    vix, vvix = minute_series(read("vix", day)), minute_series(read("vvix", day))

    # ---------- trades -> buy / sell by comparing the trade price with the bid/ask at that moment
    tq = read("tq", day)
    flows = None
    if tq is not None and len(tq):
        tq = tq[(tq["size"] > 0) & (tq["price"] > 0)].copy()
        b, a, p = tq["bid"].values, tq["ask"].values, tq["price"].values
        mid = (b + a) / 2
        valid = (a > 0) & (a >= b)
        side = np.where(~valid, 0, np.where(p >= a, 1, np.where(p <= b, -1, np.where(p > mid, 1, np.where(p < mid, -1, 0)))))
        tq["side"] = side
        tq["exp"] = pd.to_datetime(tq["expiration"]).dt.normalize()
        tq["dte"] = (tq["exp"] - d0).dt.days
        tq["t"] = pd.to_datetime(tq["trade_timestamp"])
        tq["minute"] = tq["t"].dt.floor("1min") + pd.Timedelta(minutes=1)
        tq["spx"] = spx.reindex(tq["minute"]).ffill().bfill().values
        tq["buy"] = np.where(side > 0, tq["size"], 0); tq["sell"] = np.where(side < 0, tq["size"], 0)
        tq["prem"] = tq["size"] * tq["price"] * 100
        tq["buy_prem"] = np.where(side > 0, tq["prem"], 0.0); tq["sell_prem"] = np.where(side < 0, tq["prem"], 0.0)
        # per-contract day totals
        g = tq.groupby(["exp", "strike", "right"])
        flows = g.agg(volume=("size", "sum"), buy=("buy", "sum"), sell=("sell", "sum"), trades=("size", "size"),
                      buy_prem=("buy_prem", "sum"), sell_prem=("sell_prem", "sum"), vwap=("prem", "sum"))
        flows["vwap"] = flows["vwap"] / flows["volume"].clip(lower=1) / 100
        # first-hour and last-hour flow per contract (intraday positioning changes)
        for nm, lo, hi in (("h1", "09:30", "10:30"), ("h_last", "15:00", "16:00")):
            hhmm = tq["t"].dt.hour * 100 + tq["t"].dt.minute
            m = (hhmm >= int(lo.replace(":", ""))) & (hhmm < int(hi.replace(":", "")))
            gg = tq[m].groupby(["exp", "strike", "right"])
            flows[f"buy_{nm}"] = gg["buy"].sum(); flows[f"sell_{nm}"] = gg["sell"].sum()
        # per-minute flow by expiry x right x moneyness
        tq["db"] = dte_bucket(tq["dte"].values)
        tq["mb"] = money_bucket(tq["strike"].values, tq["spx"].values, tq["right"].values)
        tq["rb"] = np.where(tq["right"] == "CALL", "c", "p")
        tq["key"] = tq["db"] + "_" + tq["rb"] + "_" + tq["mb"]
        mf = tq.groupby(["minute", "key"])[["buy", "sell"]].sum().unstack("key").fillna(0)
        mf.columns = [f"{s}_{k}" for s, k in mf.columns]
        prem = tq.groupby("minute")[["buy_prem", "sell_prem"]].sum()
        minutes_flow = mf.join(prem, how="outer")
    else:
        minutes_flow = pd.DataFrame()

    # ---------- open interest (as of the start of the day)
    oi = read("oi", day)
    oi_s = None
    if oi is not None and len(oi):
        oi["exp"] = pd.to_datetime(oi["expiration"]).dt.normalize()
        oi_s = oi.groupby(["exp", "strike", "right"])["open_interest"].last()

    # ---------- 1-minute quotes: snapshots per contract + minute-level ATM straddle / wings
    q = read("q", day)
    snaps, atm_rows = None, []
    if q is not None and len(q):
        q = q[(q["ask"] > 0) & (q["ask"] >= q["bid"])].copy()
        q["mid"] = (q["bid"] + q["ask"]) / 2
        q["exp"] = pd.to_datetime(q["expiration"]).dt.normalize()
        q["t"] = pd.to_datetime(q["timestamp"])
        q["hm"] = q["t"].dt.hour * 100 + q["t"].dt.minute          # 935 = 09:35 (integers: much faster than text)
        s = q[q["hm"].isin([int(x.replace(":", "")) for x in SNAPS])].pivot_table(index=["exp", "strike", "right"], columns="hm", values="mid", aggfunc="last")
        s.columns = [f"mid_{c:04d}" for c in s.columns]
        snaps = s
        # minute-level: nearest expiry (0DTE if listed, else next) and the next one after it
        q["dte"] = (q["exp"] - d0).dt.days
        exps = sorted(q["exp"].unique())
        sp = spx.copy(); sp.index = sp.index.hour * 100 + sp.index.minute
        for tag, ex in zip(("e1", "e2"), exps[:2]):
            qe = q[q["exp"] == ex]
            calls = qe[qe["right"] == "CALL"].pivot_table(index="hm", columns="strike", values="mid", aggfunc="last")
            puts = qe[qe["right"] == "PUT"].pivot_table(index="hm", columns="strike", values="mid", aggfunc="last")
            ks = np.array(sorted(set(calls.columns) & set(puts.columns)))
            if len(ks) < 5: continue
            for hm in calls.index:
                if hm not in sp.index: continue
                S = float(sp[hm])
                def near(level, tab):
                    k = ks[np.abs(ks - level).argmin()]
                    v = tab.at[hm, k] if (k in tab.columns and hm in tab.index) else np.nan
                    return k, v
                ka, c_atm = near(S, calls); _, p_atm = near(S, puts)
                k_p1, p1 = near(S * 0.99, puts); k_p2, p2 = near(S * 0.98, puts)
                k_c1, c1 = near(S * 1.01, calls); k_c2, c2 = near(S * 1.02, calls)
                atm_rows.append({"hm": hm, f"{tag}_dte": int((ex - d0).days), f"{tag}_k": ka, f"{tag}_straddle": c_atm + p_atm,
                                 f"{tag}_p99": p1, f"{tag}_p98": p2, f"{tag}_c101": c1, f"{tag}_c102": c2,
                                 f"{tag}_kp99": k_p1, f"{tag}_kc101": k_c1})
    # ---------- assemble the contract table
    parts = [x for x in (oi_s.to_frame() if oi_s is not None else None, flows, snaps) if x is not None]
    if not parts: return None, None
    C = pd.concat(parts, axis=1)
    C = C.reset_index()
    C = C[(C["strike"] / spx_open - 1).abs() <= WINDOW]
    C.insert(0, "date", d0)
    C["dte"] = (C["exp"] - d0).dt.days
    for hm in SNAPS:
        ts = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]} {hm}")
        C[f"spx_{hm.replace(':', '')}"] = float(spx.asof(ts)) if ts >= spx.index[0] else np.nan
    num = C.select_dtypes("float64").columns
    C[num] = C[num].astype("float32")

    # ---------- assemble the minute table
    M = pd.DataFrame({"spx": spx})
    if vix is not None: M["vix"] = vix.reindex(M.index).ffill()
    if vvix is not None: M["vvix"] = vvix.reindex(M.index).ffill()
    if len(minutes_flow): M = M.join(minutes_flow, how="left")
    if atm_rows:
        A = pd.DataFrame(atm_rows).groupby("hm").first()
        A.index = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}") + pd.to_timedelta(A.index // 100 * 60 + A.index % 100, unit="min")
        M = M.join(A, how="left")
    M.index.name = "ts"
    M = M.reset_index()
    num = M.select_dtypes("float64").columns
    M[num] = M[num].astype("float32")
    return C, M


def main():
    os.makedirs(OUT, exist_ok=True)
    folder, prefix = FILES["tq"]
    days = sorted(os.path.basename(f)[len(prefix):-8] for f in glob.glob(os.path.join(SRC, folder, prefix + "*.parquet")))
    if not days:
        folder, prefix = FILES["q"]
        days = sorted(os.path.basename(f)[len(prefix):-8] for f in glob.glob(os.path.join(SRC, folder, prefix + "*.parquet")))
    print(f"found {len(days)} days in {SRC}")
    years = sorted({d[:4] for d in days})
    t0 = time.time(); done = 0
    for y in years:
        fc, fm = os.path.join(OUT, f"contracts_{y}.parquet"), os.path.join(OUT, f"minutes_{y}.parquet")
        if os.path.exists(fc) and os.path.exists(fm) and "--redo" not in sys.argv:
            print(y, "already done - skipped"); done += sum(d[:4] == y for d in days); continue
        Cs, Ms, bad = [], [], []
        for d in [d for d in days if d[:4] == y]:
            try:
                C, M = one_day(d)
                if C is not None: Cs.append(C); Ms.append(M)
                else: bad.append(d)
            except Exception as e:
                bad.append(d); print("  day", d, "skipped:", type(e).__name__, str(e)[:120])
            done += 1
            if done % 20 == 0:
                el = time.time() - t0; print(f"  {done}/{len(days)} days, {el / 60:.0f} min so far, ~{el / done * (len(days) - done) / 60:.0f} min left")
        if Cs:
            pd.concat(Cs, ignore_index=True).to_parquet(fc, index=False, compression="zstd")
            pd.concat(Ms, ignore_index=True).to_parquet(fm, index=False, compression="zstd")
        print(y, f"saved {len(Cs)} days" + (f", {len(bad)} skipped" if bad else ""))
    tot = sum(os.path.getsize(f) for f in glob.glob(os.path.join(OUT, "*.parquet"))) / 1e6
    print(f"\nDONE - {tot:.0f} MB in {OUT}. Tell Claude it's finished.")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--test":       # one day only, prints a summary
        C, M = one_day(sys.argv[2])
        print(C.shape, M.shape); print(C.head()); print(M.iloc[::60].T.head(40))
    else:
        main()
