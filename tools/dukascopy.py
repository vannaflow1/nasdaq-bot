"""tools/dukascopy.py - free 1-minute history from Dukascopy's public datafeed (expert review 2, upgrade 1).

Used two ways:
  * SEALED EXAM DATA (sealed_exam.py): the never-seen window (NQ from Feb 2026, GC/CL from July 2026) is fetched ONLY
    inside the exam job, into the runner's memory, and thrown away afterwards. It is never written to the repo, so no
    search job, family scorer, self-check, Gemini agent or Claude session can look at it.
  * CALIBRATION (`python tools/dukascopy.py calibrate`): on months Volta HAS seen, the CFD proxy is compared with Volta's
    own futures sessions (minute-return correlation, range ratio, and the frozen F2 variants' per-trade R on both).
The instruments are CFDs, not futures: a research proxy. The calibration says how good a proxy each one is.
Format: https://datafeed.dukascopy.com/datafeed/<SYM>/<YYYY>/<MM-1>/<DD>/BID_candles_min_1.bi5 - LZMA, 24-byte records
(>i seconds-from-midnight UTC, 4 x >i prices (open, close, low, high) / point, >f volume)."""
import io, json, lzma, os, struct, sys, time, urllib.request
from datetime import date, timedelta
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
SYMS = {"NQ": "USATECHIDXUSD", "GC": "XAUUSD", "CL": "LIGHTCMDUSD", "ES": "USA500IDXUSD", "YM": "USA30IDXUSD", "RTY": "USSC2000IDXUSD"}
POINT = {"NQ": 1000, "GC": 1000, "CL": 1000, "ES": 1000, "YM": 1000, "RTY": 1000}   # checked by calibrate (price scale)
URL = "https://datafeed.dukascopy.com/datafeed/{s}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"


MISSING = []                                                   # (market, day) that could not be fetched after all retries


def _get(url, tries=7):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return b""
            time.sleep(min(60, 3 * 2 ** t))
        except Exception:
            time.sleep(min(60, 3 * 2 ** t))
    return None                                               # caller records it as missing (reported, never guessed)


CACHE = os.path.expanduser(os.environ.get("PROXY_CACHE", "~/.proxy_cache"))   # OUTSIDE the repo (never committed);
                                                               # GitHub's actions/cache keeps it between runs of the
                                                               # families / calibration workflows only


def day(mk, d, side="BID"):
    """One UTC day of 1-minute bid (or ask) candles -> DataFrame(ts_utc, o, h, l, c, v)."""
    fn = os.path.join(CACHE, mk if side == "BID" else f"{mk}_{side}", f"{d}.bi5")
    if os.path.exists(fn) and (date.today() - d).days > 3:
        raw = open(fn, "rb").read()
    else:
        raw = _get(URL.format(s=SYMS[mk], y=d.year, m=d.month - 1, d=d.day).replace("BID_candles", f"{side}_candles"))
        if raw is not None and (date.today() - d).days > 3:
            os.makedirs(os.path.dirname(fn), exist_ok=True); open(fn, "wb").write(raw)
    if raw is None: MISSING.append((mk, str(d))); return pd.DataFrame()
    if not raw: return pd.DataFrame()
    b = lzma.decompress(raw); n = len(b) // 24
    rec = np.frombuffer(b[:n * 24], dtype=np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    p = POINT[mk]; t0 = pd.Timestamp(d)
    df = pd.DataFrame({"ts": t0 + pd.to_timedelta(rec["t"].astype(np.int64), unit="s"), "o": rec["o"] / p, "h": rec["h"] / p,
                       "l": rec["l"] / p, "c": rec["c"] / p, "v": rec["v"].astype(float)})
    return df[df.v > 0]                                       # Dukascopy pads closed minutes with flat zero-volume candles


def fetch(mk, start, end, workers=3, side="BID"):
    """All 1-minute bars between two dates, timestamps converted to Chicago time (Volta's session clock)."""
    from concurrent.futures import ThreadPoolExecutor
    days = [start + timedelta(i) for i in range((end - start).days + 1)]
    with ThreadPoolExecutor(workers) as ex: parts = list(ex.map(lambda d: day(mk, d, side), days))
    n = pd.concat([p for p in parts if len(p)], ignore_index=True) if any(len(p) for p in parts) else pd.DataFrame()
    if not len(n): return n
    n["ts"] = n.ts.dt.tz_localize("UTC").dt.tz_convert("America/Chicago").dt.tz_localize(None)
    n["sym"] = SYMS[mk]
    return n.sort_values("ts").reset_index(drop=True)


def sessions(n):
    """Same session layout as tools/build_market_bars.py: 390 bars 08:30-15:00 CT + levels known at the open."""
    n = n.copy(); n["sess"] = n.ts.dt.normalize() + pd.to_timedelta((n.ts.dt.hour >= 17).astype(int), unit="D")
    n["m"] = n.ts.dt.hour * 60 + n.ts.dt.minute
    grid = np.arange(510, 900); O, H, L, C, V, meta = [], [], [], [], [], []; prev = None
    for s, g in n.groupby("sess"):
        if s.weekday() >= 5: continue
        rth = g[(g.m >= 510) & (g.m < 900)].set_index("m")
        if len(rth) < 300: prev = None; continue
        rth = rth[~rth.index.duplicated()].reindex(grid)
        rth["c"] = rth.c.ffill().bfill()
        for c in ("o", "h", "l"): rth[c] = rth[c].fillna(rth.c)
        rth["v"] = rth.v.fillna(0)
        on = g[(g.m >= 17 * 60) | (g.m < 510)]; asia = g[(g.m >= 18 * 60) | (g.m < 120)]; lon = g[(g.m >= 120) & (g.m < 420)]
        mid = g[((g.m >= 23 * 60) & (g.ts.dt.normalize() < s)) | ((g.m < 510) & (g.ts.dt.normalize() == s))]
        if len(on) < 200 or len(mid) < 100: prev = None; continue
        tp = (mid.h + mid.l + mid.c) / 3
        r = {"session": s.strftime("%Y-%m-%d"), "sym": g.sym.iloc[0], "open": float(rth.o.iloc[0]),
             "on_high": float(on.h.max()), "on_low": float(on.l.min()), "asia_high": float(asia.h.max()) if len(asia) else np.nan,
             "asia_low": float(asia.l.min()) if len(asia) else np.nan,
             "london_high": float(lon.h.max()) if len(lon) else np.nan, "london_low": float(lon.l.min()) if len(lon) else np.nan,
             "midnight_open": float(mid.o.iloc[0]), "vw_pv": float((tp * mid.v).sum()), "vw_v": float(mid.v.sum()),
             "vw_pv2": float((tp * tp * mid.v).sum()), "rng": float(rth.h.max() - rth.l.min()) / float(rth.o.iloc[0])}
        if prev: r.update(yday_high=prev[0], yday_low=prev[1], yday_close=prev[2])
        meta.append(r)
        O.append(rth.o.values); H.append(rth.h.values); L.append(rth.l.values); C.append(rth.c.values); V.append(rth.v.values)
        prev = (float(rth.h.max()), float(rth.l.min()), float(rth.c.iloc[-1]))
    M = pd.DataFrame(meta)
    if not len(M): return None, M
    M["fc_frac"] = M.rng.shift(1).rolling(20, min_periods=10).mean()
    M["date"] = M.session.shift(1)                            # memory date = previous session (evening before)
    for c in ("pw_takes_pdh", "pw_takes_pdl", "pw_gap_fill", "pw_tail_day"): M[c] = np.nan
    M = M.drop(columns=["rng"])
    A = {k: np.array(v, np.float64) for k, v in zip("OHLCV", (O, H, L, C, V))}
    return A, M


def calibrate(markets=("GC", "CL", "NQ"), start=date(2025, 4, 1), end=date(2025, 6, 13)):
    """On months Volta has already seen: how close is each CFD proxy to Volta's own futures data?"""
    import strategy_lab as S, families as F, test_engine as TE
    _, X = TE.frame(); out = {}
    fam = next(f for f in json.load(open(F.REG)) if f["id"] == "F2")
    for mk in markets:
        t0 = time.time(); n = fetch(mk, start - timedelta(45), end)
        if not len(n): out[mk] = {"error": "no data"}; continue
        A, Mp = sessions(n); Df = S.data(mk); Mf = Df["M"]
        import sealed as SE
        Mp = SE.match_futures_inputs(Mp, mk, X)               # NQ: the brain's stop forecast, as in the futures backtest
        common = sorted(set(Mp.session) & set(Mf.session[(Mf.session >= str(start)) & (Mf.session <= str(end))]))
        ip = {s: i for i, s in enumerate(Mp.session)}; jf = {s: i for i, s in enumerate(Mf.session)}
        rp = np.concatenate([np.diff(np.log(A["C"][ip[s]])) for s in common]); rf = np.concatenate([np.diff(np.log(Df["C"][jf[s]])) for s in common])
        ok = np.isfinite(rp) & np.isfinite(rf)
        scale = float(np.median([A["C"][ip[s]][-1] / Df["C"][jf[s]][-1] for s in common]))
        rr = float(np.median([(A["H"][ip[s]].max() - A["L"][ip[s]].min()) / (Df["H"][jf[s]].max() - Df["L"][jf[s]].min()) for s in common]))
        res = {"sessions": len(common), "minute_return_corr": round(float(np.corrcoef(rp[ok], rf[ok])[0, 1]), 3),
               "price_ratio_proxy_over_futures": round(scale, 4), "range_ratio": round(rr, 3), "fetch_s": round(time.time() - t0)}
        # the frozen F2 variants on both, same sessions: does the proxy give the same trades?
        if mk == "NQ" or True:
            V = F.variants(fam); pairs = []
            S.install_market(mk + "_PROXY", A, Mp, like=mk)
            ip_idx = np.array([ip[s] for s in common]); jf_idx = np.array([jf[s] for s in common])
            for v in V[::5]:
                for sp in v["sleeve"]:
                    sf = dict(sp, market=mk); spp = dict(sp, market=mk + "_PROXY")
                    Tf = S.backtest(sf, X, jf_idx); Tp = S.backtest(spp, X, ip_idx)
                    if len(Tf) and len(Tp):
                        a = Tf.groupby("session").R.sum(); b = Tp.groupby("session").R.sum(); j = a.index.intersection(b.index)
                        if len(j) > 10: pairs.append((float(np.corrcoef(a[j], b[j])[0, 1]), float(a.mean()), float(b.mean()), len(a), len(b)))
            if pairs:
                P = np.array(pairs)
                res["F2_daily_R_corr_median"] = round(float(np.median(P[:, 0])), 3)
                res["F2_mean_R_futures"] = round(float(P[:, 1].mean()), 3); res["F2_mean_R_proxy"] = round(float(P[:, 2].mean()), 3)
                res["F2_trade_days_ratio"] = round(float(P[:, 4].sum() / max(P[:, 3].sum(), 1)), 3)
        res["missing_days"] = sum(1 for m, _ in MISSING if m == mk)
        out[mk] = res; print(mk, res, flush=True)
        fn = os.path.join(HERE, "knowledge", "research_out", "proxy_calibration.json")    # save after every market
        old = json.load(open(fn)) if os.path.exists(fn) else {}; old[mk] = res; os.makedirs(os.path.dirname(fn), exist_ok=True)
        json.dump(old, open(fn, "w"), indent=1)
    out["window"] = f"{start}..{end} (already seen by Volta - calibration only)"
    os.makedirs(os.path.join(HERE, "knowledge", "research_out"), exist_ok=True)
    fn = os.path.join(HERE, "knowledge", "research_out", "proxy_calibration.json")
    old = json.load(open(fn)) if os.path.exists(fn) else {}
    old.update(out); json.dump(old, open(fn, "w"), indent=1)
    return out


def nq_detail(start=date(2025, 4, 1), end=date(2025, 6, 13)):
    """Expert review 4 (22 Oct 2026): WHY does the NQ proxy not reproduce F2's futures trades (daily-R corr 0.67, bias
    -0.11R) when GC/CL do (0.96 / 0.91)? On the same already-seen calibration window, three price constructions of the
    CFD - bid candles (current), ask candles, mid = (bid + ask) / 2 - are compared with Volta's futures: F2 daily-R
    correlation, mean R, and whether each session's FIRST trade has the same minute and side. Also measured: the spread
    at the 08:30 CT open versus the rest of the session, and the gap between the proxy's and the futures' open (after the
    basis). Never touches the sealed window (Feb-Oct 2026). Output: knowledge/research_out/proxy_nq_detail.json."""
    import strategy_lab as S, families as F, test_engine as TE
    _, X = TE.frame(); out = {"window": f"{start}..{end} (already seen - calibration only)"}
    fn = os.path.join(HERE, "knowledge", "research_out", "proxy_nq_detail.json")
    nb = fetch("NQ", start - timedelta(45), end, side="BID"); na = fetch("NQ", start - timedelta(45), end, side="ASK")
    if not len(nb) or not len(na): out["error"] = "no data"; json.dump(out, open(fn, "w"), indent=1); return out
    m = nb.merge(na[["ts", "o", "h", "l", "c"]], on="ts", suffixes=("", "_a"))
    mid = pd.DataFrame({"ts": m.ts, "o": (m.o + m.o_a) / 2, "h": (m.h + m.h_a) / 2, "l": (m.l + m.l_a) / 2,
                        "c": (m.c + m.c_a) / 2, "v": m.v, "sym": m.sym})
    sp = (m.c_a - m.c); mm = m.ts.dt.hour * 60 + m.ts.dt.minute
    out["spread_pts"] = {"median_rth": round(float(sp[(mm >= 510) & (mm < 900)].median()), 2),
                         "median_0830_bar": round(float(sp[mm == 510].median()), 2), "p90_0830_bar": round(float(sp[mm == 510].quantile(0.9)), 2),
                         "median_0730_bar": round(float(sp[mm == 450].median()), 2), "median_overnight": round(float(sp[(mm < 450) | (mm >= 960)].median()), 2)}
    print("spread", out["spread_pts"], flush=True)
    Df = S.data("NQ"); Mf = Df["M"]; jf = {s: i for i, s in enumerate(Mf.session)}
    fam2 = next(f for f in json.load(open(F.REG)) if f["id"] == "F2"); V = F.variants(fam2)
    fam10 = next(f for f in json.load(open(F.REG)) if f["id"] == "F10"); v43 = F.variants(fam10)[int(fam10["forward_variant"])]
    tests = [("F2 v" + str(i), V[i]["sleeve"][0]) for i in range(0, len(V), 5)] + [("F10 v43", v43["sleeve"][0])]
    import sealed as SE
    builds = []
    for pname, n in (("bid", nb), ("ask", na), ("mid", mid)):
        A, Mp0 = sessions(n)
        builds.append((pname + "|realized20", A, Mp0))                        # stop input as dukascopy.sessions makes it
        builds.append((pname + "|brain", A, SE.match_futures_inputs(Mp0, "NQ", X)))   # the futures backtest's input
    for name, A, Mp in builds:
        ip = {s: i for i, s in enumerate(Mp.session)}
        common = sorted(set(Mp.session) & set(Mf.session[(Mf.session >= str(start)) & (Mf.session <= str(end))]))
        S.install_market("NQ_PX_" + name.replace("|", "_").upper(), A, Mp, like="NQ")
        ipx = np.array([ip[s] for s in common]); jfx = np.array([jf[s] for s in common])
        scale = float(np.median([A["C"][ip[s]][-1] / Df["C"][jf[s]][-1] for s in common]))
        od = np.array([A["O"][ip[s]][0] / scale - Df["O"][jf[s]][0] for s in common])           # open gap after the basis
        c5 = np.array([A["C"][ip[s]][4] / scale - Df["C"][jf[s]][4] for s in common])           # same at 08:34
        res = {"sessions": len(common), "basis_ratio": round(scale, 5), "open_diff_pts_median_abs": round(float(np.median(np.abs(od))), 2),
               "open_diff_pts_p90_abs": round(float(np.quantile(np.abs(od), 0.9)), 2), "close_0834_diff_pts_median_abs": round(float(np.median(np.abs(c5))), 2),
               "tests": {}}
        for tname, spec in tests:
            Tf = S.backtest(dict(spec, market="NQ"), X, jfx); Tp = S.backtest(dict(spec, market="NQ_PX_" + name.replace("|", "_").upper()), X, ipx)
            if not len(Tf) or not len(Tp): continue
            a = Tf.groupby("session").R.sum(); b = Tp.groupby("session").R.sum(); j = a.index.union(b.index)
            a, b = a.reindex(j).fillna(0.0), b.reindex(j).fillna(0.0)
            f1 = Tf.sort_values("k").groupby("session").first(); p1 = Tp.sort_values("k").groupby("session").first()
            both = f1.index.intersection(p1.index)
            same = float(np.mean((f1.loc[both, "k"].values == p1.loc[both, "k"].values) & (f1.loc[both, "side"].values == p1.loc[both, "side"].values))) if len(both) else np.nan
            res["tests"][tname] = {"daily_R_corr": round(float(np.corrcoef(a, b)[0, 1]), 3), "mean_R_futures": round(float(Tf.R.mean()), 3),
                                   "mean_R_proxy": round(float(Tp.R.mean()), 3), "trades_futures": int(len(Tf)), "trades_proxy": int(len(Tp)),
                                   "first_trade_same_minute_and_side": round(same, 3), "trade_days_only_one": int(len(j) - len(both))}
        t = res["tests"]
        res["summary"] = {"median_daily_R_corr": round(float(np.median([x["daily_R_corr"] for x in t.values()])), 3),
                          "mean_bias_R": round(float(np.mean([x["mean_R_proxy"] - x["mean_R_futures"] for x in t.values()])), 3),
                          "median_first_trade_match": round(float(np.median([x["first_trade_same_minute_and_side"] for x in t.values()])), 3)}
        out[name] = res; print(name, res["summary"], {k: res[k] for k in ("open_diff_pts_median_abs", "close_0834_diff_pts_median_abs")}, flush=True)
        os.makedirs(os.path.dirname(fn), exist_ok=True); json.dump(out, open(fn, "w"), indent=1)
    out["missing_days"] = len(MISSING); json.dump(out, open(fn, "w"), indent=1)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["calibrate"]: calibrate()
    elif sys.argv[1:2] == ["nq_detail"]: nq_detail()
    elif sys.argv[1:2] == ["probe"]:                          # quick format/scale probe on a seen day
        for mk in SYMS: d = day(mk, date(2025, 6, 4)); print(mk, len(d), d.iloc[[0, len(d) // 2, -1]].to_dict("records") if len(d) else "", flush=True)
        print("missing:", MISSING)
