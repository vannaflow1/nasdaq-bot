"""strategy_forward.py - every evening: (1) trade each strategy that passed the locked exam on TODAY's real bars, with the
exact same rules and fills as the backtest (rules fixed before the day = a true forward test), (2) update the /strategies
status with the lab's scoreboard. Never changes anything else; any error just skips the forward test."""
import json, math, os, sys, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
import strategy_lab as S
CT, LUX = ZoneInfo("America/Chicago"), ZoneInfo("Europe/Luxembourg")
FWD, STATUS = os.path.join(K, "strategy_forward.csv"), os.path.join(HERE, "status.json")
HOOK = os.environ.get("DISCORD_WEBHOOK_LEARN") or os.environ.get("DISCORD_WEBHOOK_BRAIN") or None


def entries():
    return [json.loads(l) for l in open(S.LOG) if l.strip()] if os.path.exists(S.LOG) else []


def candidates(E):
    out = {}
    for e in E:
        if str(e.get("verdict", "")).startswith("PROMISING STRATEGY"):
            out[S.spec_id(e["spec"])] = e
    return list(out.values())


def yahoo_bars(sym="NQ%3DF"):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=5d&includePrePost=true"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"ts": [datetime.fromtimestamp(t, timezone.utc).astimezone(CT).replace(tzinfo=None) for t in r["timestamp"]],
                       "Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"], "Volume": q.get("volume")}).dropna(subset=["Close"])
    df["Volume"] = df.Volume.fillna(0); df["m"] = df.ts.dt.hour * 60 + df.ts.dt.minute
    return df


def today_session(df, day):
    """Same construction as the historical lab data (brain/strat_build.py) for one live session."""
    s = pd.Timestamp(day); prev = s - pd.Timedelta(days=1)
    g = df[((df.ts.dt.normalize() == prev) & (df.m >= 17 * 60)) | ((df.ts.dt.normalize() == s) & (df.m < 16 * 60))]
    rth = g[(g.ts.dt.normalize() == s) & (g.m >= 510) & (g.m < 900)].set_index("m")
    if len(rth) < 370: return None
    rth = rth[~rth.index.duplicated()].reindex(np.arange(510, 900))
    rth["Close"] = rth.Close.ffill().bfill()
    for c in ("Open", "High", "Low"): rth[c] = rth[c].fillna(rth.Close)
    rth["Volume"] = rth.Volume.fillna(0)
    on = g[(g.ts.dt.normalize() == prev) | (g.m < 510)]
    asia = g[((g.ts.dt.normalize() == prev) & (g.m >= 18 * 60)) | ((g.ts.dt.normalize() == s) & (g.m < 120))]
    lon = g[(g.ts.dt.normalize() == s) & (g.m >= 120) & (g.m < 420)]
    mid = g[((g.ts.dt.normalize() == prev) & (g.m >= 23 * 60)) | ((g.ts.dt.normalize() == s) & (g.m < 510))]
    pd_rth = df[(df.ts.dt.normalize() < s) & (df.m >= 510) & (df.m < 900)]
    yd = pd_rth[pd_rth.ts.dt.normalize() == pd_rth.ts.dt.normalize().max()] if len(pd_rth) else pd_rth
    tp = (mid.High + mid.Low + mid.Close) / 3
    meta = {"session": s.strftime("%Y-%m-%d"), "open": float(rth.Open.iloc[0]), "on_high": float(on.High.max()), "on_low": float(on.Low.min()),
            "asia_high": float(asia.High.max()), "asia_low": float(asia.Low.min()),
            "london_high": float(lon.High.max()) if len(lon) else np.nan, "london_low": float(lon.Low.min()) if len(lon) else np.nan,
            "midnight_open": float(mid.Open.iloc[0]) if len(mid) else np.nan, "vw_pv": float((tp * mid.Volume).sum()),
            "vw_v": float(mid.Volume.sum()), "vw_pv2": float((tp * tp * mid.Volume).sum()),
            "yday_high": float(yd.High.max()) if len(yd) else np.nan, "yday_low": float(yd.Low.min()) if len(yd) else np.nan,
            "yday_close": float(yd.Close.iloc[-1]) if len(yd) else np.nan}
    meta["yday_mid"] = (meta["yday_high"] + meta["yday_low"]) / 2
    arrs = {k: rth[c].values.astype(float) for k, c in (("O", "Open"), ("H", "High"), ("L", "Low"), ("C", "Close"), ("V", "Volume"))}
    return meta, arrs


def today_known(meta, st):
    """Known-at-the-open values for today, in the same columns the backtest filters use."""
    import csv
    row = {}
    try:
        rows = [r for r in csv.DictReader(open(os.path.join(HERE, "brain_preds.csv"))) if r.get("next_date", "")[:10] == meta["session"]]
        if rows:
            f = json.loads(rows[-1]["feat"]); row.update(f); memdate = rows[-1]["date"][:10]
            for a, b in (("iv30", "l_iv30"), ("rv20", "l_rv20"), ("impl", "l_impl"), ("rng", "l_rng"), ("rng5", "l_rng5"), ("rng20", "l_rng20")):
                if b in f: row[a] = math.exp(float(f[b]))
            if "iv30" in row and "rv20" in row: row["vrp"] = row["iv30"] - row["rv20"]
            meta["fc_frac"] = math.exp(float(f["l_bot"])) if "l_bot" in f else np.nan
        else:
            return None, None
    except Exception as e:
        print("no evening features:", e); return None, None
    try:                                                       # today's red-folder news flags (live calendar)
        import redfolder
        row.update({k: v for k, v in redfolder.today_flags(meta["session"]).items() if k.startswith("k_")})
    except Exception as e:
        print("no news flags:", e)
    pr = st.get("powers_raw") or {}
    if pr.get("date") == meta["session"]:
        row.update({k: v for k, v in pr.items() if k.startswith("pw_")})
    o = meta["open"]
    if np.isfinite(meta.get("yday_close", np.nan)):
        row["k_gap"] = (o - meta["yday_close"]) / meta["yday_close"] * 100
        row["k_open_vs_yday"] = (o - meta["yday_low"]) / max(meta["yday_high"] - meta["yday_low"], 1e-9)
    row["k_on_range"] = (meta["on_high"] - meta["on_low"]) / o * 100
    row["k_on_pos"] = (o - meta["on_low"]) / max(meta["on_high"] - meta["on_low"], 1e-9)
    try:
        mac = pd.read_csv(os.path.join(K, "macro_daily.csv"), parse_dates=["date"]).set_index("date")
        if pd.Timestamp(memdate) in mac.index: row.update(mac.loc[pd.Timestamp(memdate)].dropna().to_dict())
    except Exception:
        pass
    return memdate, row


YSYM = {"NQ": "NQ%3DF", "GC": "GC%3DF", "CL": "CL%3DF"}


def forward(cands, st):
    """Trade every exam-passed strategy on today's real 1-minute bars of ITS market (NQ, gold or oil)."""
    import test_engine as T
    day = datetime.now(CT).date()
    if datetime.now(CT).hour < 15 or day.weekday() >= 5:
        print("session not finished yet"); return []
    _, X0 = T.frame(); out = []; memdate = None
    for mk in sorted({(c["spec"].get("market") or "NQ").upper() for c in cands}):
        try:
            built = today_session(yahoo_bars(YSYM[mk]), day)
        except Exception as e:
            print(mk, "bars failed:", e); continue
        if not built: print(mk, "no full session today"); continue
        meta, arrs = built
        if mk == "NQ":
            memdate, row = today_known(meta, st)
            if row is None: continue
        else:                                                   # gold/oil: own expected range from its last 20 sessions
            Dm = S.data(mk); rr = (Dm["H"].max(1) - Dm["L"].min(1)) / Dm["O"][:, 0]
            meta["fc_frac"] = float(np.nanmean(rr[-20:]))
            nq_meta = today_session(yahoo_bars(YSYM["NQ"]), day)
            memdate, row = today_known(nq_meta[0], st) if nq_meta else (None, None)
            if row is None: continue
        D = dict(S.data(mk)); Mx = D["M"]
        meta["date"] = memdate
        keep = (Mx.session != meta["session"]).values                   # keep table and bar arrays in lock-step
        D["M"] = pd.concat([Mx[keep], pd.DataFrame([meta])], ignore_index=True); D["M"].attrs = Mx.attrs
        for k in "OHLCV": D[k] = np.vstack([D[k][keep], arrs[k][None, :]])
        i = len(D["M"]) - 1
        X = pd.concat([X0[X0.index != pd.Timestamp(memdate)], pd.DataFrame([row], index=[pd.Timestamp(memdate)])]).sort_index()
        S._MK[mk] = D if mk != "NQ" else S._MK.get(mk)                  # filters read the extended table
        if mk == "NQ": S._DATA.update(D)
        for c in [c for c in cands if (c["spec"].get("market") or "NQ").upper() == mk]:
            spec = c["spec"]
            try:
                allow, side = S._filters(spec, X)
                r = S.simulate_session(D, i, spec, side=side[i]) if allow[i] else None
            except Exception as e:
                print("forward failed for", c["name"], e); continue
            out.append({"date": meta["session"], "market": mk, "id": S.spec_id(spec), "name": c["name"], "traded": bool(r),
                        "pnl_pts": round(r[0], 4) if r else 0.0, "R": round(r[1], 2) if r else 0.0, "side": int(r[2]) if r else 0})
    if out:
        F = pd.read_csv(FWD) if os.path.exists(FWD) else pd.DataFrame()
        F = pd.concat([F[~((F.get("date") == out[0]["date"]))] if len(F) else F, pd.DataFrame(out)], ignore_index=True)
        F.to_csv(FWD, index=False)
    return out


def main():
    E = entries(); C = candidates(E)
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    today = []
    if C:
        try:
            today = forward(C, st)
        except Exception as e:
            print("forward test skipped:", type(e).__name__, e)
    ex = json.load(open(S.EXAMS)) if os.path.exists(S.EXAMS) else {}
    near = sorted([e for e in E if (e.get("insample") or {}).get("n", 0) >= 100], key=lambda e: -e["insample"].get("avg_R", -9))[:3]
    lines = [f"STRATEGY LAB - {len(E)} strategies tested ({sum(e.get('source') == 'curiosity' for e in E)} designed by Volta itself), "
             f"{sum(ex.values())} locked exams taken, {len(C)} passed."]
    F = pd.read_csv(FWD) if os.path.exists(FWD) else pd.DataFrame()
    if C:
        lines += ["", "PASSED THE EXAM - now forward-tested every day:"]
        for c in C:
            f = F[(F.id == S.spec_id(c["spec"])) & (F.traded)] if len(F) else F
            live = (f"live {len(f)} trades, {f.R.sum():+.1f}R total, win {(f.R > 0).mean():.0%}" if len(f) else "no live trades yet")
            lines.append(f"- {c['name']}: exam {c['exam'].get('avg_R', 0):+.2f}R/trade; {live}")
    else:
        lines += ["", "Nothing has passed the locked 2024-2026 exam yet. Closest in-sample (2014-2023, after costs):"]
    lines += [f"- {e['name'][:80]}: {e['insample']['n']} trades, {e['insample']['avg_R']:+.2f}R/trade, positive {e['insample']['years_pos']} years"
              for e in near]
    lines.append("Every strategy: pessimistic 1-minute fills + costs, must beat random entries, survive a stress test and pass a locked exam.")
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    st["strategies"] = lines; json.dump(st, open(STATUS, "w"), indent=1)
    try:
        import eta; eta.update()                                  # forward-test days changed: refresh the edge estimate
    except Exception as e:
        print("eta skipped:", type(e).__name__, e)
    print("\n".join(lines))
    if today and HOOK:
        import qqq_gex_daily as q
        body = "\n".join(f"{t['name'][:70]}: " + (f"{'LONG' if t['side'] > 0 else 'SHORT'} {t['R']:+.2f}R ({t['pnl_pts']:+.1f} pts)" if t["traded"] else "no setup today")
                         for t in today)
        q.push("Strategy forward test - today", body, tags="robot", hook=HOOK)


if __name__ == "__main__":
    main()
