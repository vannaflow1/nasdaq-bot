"""discovered_read.py - each morning right after the NY open: evaluates every power Volta discovered itself
(knowledge/discovered_powers.json: questions that survived the stress test) on today's known-at-open values and posts
where today falls and what history says. Runs inside the session loop; once per day; never affects anything else."""
import json, math, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
CT, LUX = ZoneInfo("America/Chicago"), ZoneInfo("Europe/Luxembourg")
DISC, ST = os.path.join(K, "discovered_powers.json"), os.path.join(K, "discovered_state.json")
STATUS = os.path.join(HERE, "status.json")
HOOK = os.environ.get("DISCORD_WEBHOOK_LIVE") or os.environ.get("DISCORD_WEBHOOK") or None


def premarket(df, day):
    s = pd.Timestamp(day); prev = s - pd.Timedelta(days=1)
    g = df[((df.ts.dt.normalize() == prev) & (df.m >= 17 * 60)) | ((df.ts.dt.normalize() == s) & (df.m < 16 * 60))]
    ny = g[(g.ts.dt.normalize() == s) & (g.m >= 510)]
    if ny.empty: return None
    on = g[(g.ts.dt.normalize() == prev) | (g.m < 510)]
    asia = g[((g.ts.dt.normalize() == prev) & (g.m >= 18 * 60)) | ((g.ts.dt.normalize() == s) & (g.m < 120))]
    lon = g[(g.ts.dt.normalize() == s) & (g.m >= 120) & (g.m < 420)]; pre = g[(g.ts.dt.normalize() == s) & (g.m >= 120) & (g.m < 510)]
    yd_all = df[(df.ts.dt.normalize() < s) & (df.m >= 510) & (df.m < 900)]
    yd = yd_all[yd_all.ts.dt.normalize() == yd_all.ts.dt.normalize().max()]
    o = float(ny.Open.iloc[0]); ah, al = float(asia.High.max()), float(asia.Low.min())
    meta = {"session": s.strftime("%Y-%m-%d"), "open": o, "on_high": float(on.High.max()), "on_low": float(on.Low.min()),
            "yday_high": float(yd.High.max()), "yday_low": float(yd.Low.min()), "yday_close": float(yd.Close.iloc[-1])}
    extra = {"k_asia_range": (ah - al) / o * 100, "k_open_vs_asia": (o - al) / max(ah - al, 1e-9),
             "k_on_return": (o / float(on.Open.iloc[0]) - 1) * 100, "k_dow": float(s.dayofweek),
             "k_yday_range": (meta["yday_high"] - meta["yday_low"]) / o * 100}
    if len(lon):
        lh, ll = float(lon.High.max()), float(lon.Low.min())
        extra.update(k_london_range=(lh - ll) / o * 100, k_open_vs_london=(o - ll) / max(lh - ll, 1e-9))
    if len(pre): extra.update(k_london_took_asia_high=float(pre.High.max() > ah), k_london_took_asia_low=float(pre.Low.min() < al))
    return meta, extra


def main():
    if not os.path.exists(DISC): return
    D = [d for d in json.load(open(DISC)) if d.get("active", True)]
    now = datetime.now(CT)
    if not D or now.weekday() >= 5 or now.hour * 60 + now.minute < 512: return
    st = json.load(open(ST)) if os.path.exists(ST) else {}
    if st.get("date") == str(now.date()): return
    import strategy_forward as F, test_engine as T
    pm = premarket(F.yahoo_bars(), now.date())
    if not pm: print("no NY open yet"); return
    meta, extra = pm
    try:                                                        # ES vs NQ before the open (SMT divergence at the Asia high/low)
        pe = premarket(F.yahoo_bars("ES%3DF"), now.date())
        if pe and "k_london_took_asia_high" in extra and "k_london_took_asia_high" in pe[1]:
            nh, eh = extra["k_london_took_asia_high"], pe[1]["k_london_took_asia_high"]
            nl, el = extra["k_london_took_asia_low"], pe[1]["k_london_took_asia_low"]
            extra.update(k_smt_high=float(nh != eh), k_smt_high_nq_only=float(nh == 1 and eh == 0),
                         k_smt_low=float(nl != el), k_smt_low_nq_only=float(nl == 1 and el == 0))
    except Exception as e:
        print("no ES pre-market:", e)
    status = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    memdate, row = F.today_known(meta, status)
    if row is None: print("no evening features for today"); return
    row.update(extra)
    try:
        ss = pd.read_csv(os.path.join(K, "session_table.csv"))
        r20 = ss.y_range.tail(20).mean()                      # last known 20-session NY range (approximation live)
        row["k_range20"] = r20; row["k_on_vs_normal"] = row["k_on_range"] / r20
    except Exception:
        pass
    _, X = T.frame()
    hist = X.copy()
    X = pd.concat([X[X.index != pd.Timestamp(memdate)], pd.DataFrame([row], index=[pd.Timestamp(memdate)])]).sort_index()
    lines = []
    for d in D:
        try:
            v = T.evaluate(d["expr"], X); tv = v.get(pd.Timestamp(memdate))
            hv = T.evaluate(d["expr"], hist); tg = T.evaluate(d["target"], hist, allow=T.TARGET_OK)
            H = pd.DataFrame({"s": hv, "y": tg}).replace([np.inf, -np.inf], np.nan).dropna()
            if tv is None or not np.isfinite(tv) or len(H) < 300: continue
            if H.s.nunique() <= 2:                                     # yes/no input: compare like with like
                grp = H[H.s == tv]; name = "yes" if tv > 0 else "no"
            else:
                edges = np.quantile(H.s, [0.2, 0.4, 0.6, 0.8]); q = int(np.searchsorted(edges, tv))
                grp = H[np.searchsorted(edges, H.s.values) == q]; name = ["bottom fifth", "low", "middle", "high", "top fifth"][q] + " of history"
            binary = set(np.unique(H.y)) <= {0.0, 1.0}
            f = (lambda x: f"{x:.0%}") if binary else (lambda x: f"{x:.3g}")
            lines.append(f"⚡ {d['question']}\n   today: {name} -> {f(grp.y.mean())} on such days ({len(grp)} in history; all days {f(H.y.mean())})")
        except Exception as e:
            print("power", d.get("id"), "skipped:", e)
    st["date"] = str(now.date()); json.dump(st, open(ST, "w"))
    if not lines: return
    head = f"POWERS VOLTA DISCOVERED ITSELF - {now:%a %d %b}"
    status = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    status["powers"] = [l for l in (status.get("powers") or []) if not l.startswith(("⚡", "   today:", "POWERS VOLTA"))] + ["", head] + lines
    json.dump(status, open(STATUS, "w"), indent=1)
    print("\n".join([head] + lines))
    if HOOK:
        import qqq_gex_daily as qg
        qg.push(head, "\n".join(lines) + "\n\nSelf-discovered (survived stress test). Base rates, not signals.", tags="zap", hook=HOOK)


if __name__ == "__main__":
    main()
