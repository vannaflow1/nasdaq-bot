"""Strategy-lab data for another futures market (GC gold, CL crude oil), same layout as NQ's strat_bars.npz:
per session 390 one-minute bars 08:30-15:00 CT + levels known at the open (overnight, Asia, London, midnight open,
VWAP accumulators, yesterday's high/low/close). 'date' = the memory date (evening before) so Volta's filters line up;
fc_frac = this market's own expected range (20-session average high-low range, past only); powers (pw_*) are NQ-only."""
import sys, numpy as np, pandas as pd
mk = sys.argv[1].upper(); src = sys.argv[2]
n = pd.read_csv(src, parse_dates=["ts"])
n["sess"] = n.ts.dt.normalize() + pd.to_timedelta((n.ts.dt.hour >= 17).astype(int), unit="D")
n["m"] = n.ts.dt.hour * 60 + n.ts.dt.minute
grid = np.arange(510, 900); O, H, L, C, V, meta = [], [], [], [], [], []; prev = None
for s, g in n.groupby("sess"):
    sym = g.sym.mode().iloc[0]; g = g[g.sym == sym]
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
    r = {"session": s.strftime("%Y-%m-%d"), "sym": sym, "open": float(rth.o.iloc[0]),
         "on_high": float(on.h.max()), "on_low": float(on.l.min()), "asia_high": float(asia.h.max()) if len(asia) else np.nan,
         "asia_low": float(asia.l.min()) if len(asia) else np.nan,
         "london_high": float(lon.h.max()) if len(lon) else np.nan, "london_low": float(lon.l.min()) if len(lon) else np.nan,
         "midnight_open": float(mid.o.iloc[0]), "vw_pv": float((tp * mid.v).sum()), "vw_v": float(mid.v.sum()), "vw_pv2": float((tp * tp * mid.v).sum()),
         "rng": float(rth.h.max() - rth.l.min()) / float(rth.o.iloc[0])}
    if prev and prev[0] == sym: r.update(yday_high=prev[1], yday_low=prev[2], yday_close=prev[3])
    meta.append(r)
    O.append(rth.o.values); H.append(rth.h.values); L.append(rth.l.values); C.append(rth.c.values); V.append(rth.v.values)
    prev = (sym, float(rth.h.max()), float(rth.l.min()), float(rth.c.iloc[-1]))
M = pd.DataFrame(meta)
M["fc_frac"] = M.rng.shift(1).rolling(20, min_periods=10).mean()          # past only
M["date"] = M.session.shift(1)                                            # memory date = previous session (evening before)
sys.path.insert(0, "/home/claude/nasdaq-bot")
try:                                                                      # align to NQ's memory dates where they exist
    import idea_lab as I
    mem = I.memory(); nd = pd.DatetimeIndex(mem.index + pd.to_timedelta(mem.gap_days.fillna(1).values, unit="D"))
    mp = pd.Series(mem.index, index=nd); mp = mp[~mp.index.duplicated()]
    m2 = pd.to_datetime(M.session).map(mp)
    M["date"] = np.where(m2.notna(), m2.dt.strftime("%Y-%m-%d"), M.date)
except Exception as e:
    print("memory alignment skipped:", e)
for c in ("pw_takes_pdh", "pw_takes_pdl", "pw_gap_fill", "pw_tail_day"): M[c] = np.nan
M = M.drop(columns=["rng"])
k = mk.lower()
np.savez_compressed(f"/home/claude/nasdaq-bot/knowledge/strat_bars_{k}.npz", O=np.array(O, np.float32), H=np.array(H, np.float32),
                    L=np.array(L, np.float32), C=np.array(C, np.float32), V=np.array(V, np.float32))
M.round(5).to_csv(f"/home/claude/nasdaq-bot/knowledge/strat_sessions_{k}.csv", index=False)
print(mk, len(M), "sessions", M.session.iloc[0], "->", M.session.iloc[-1], "| median expected range", round(M.fc_frac.median() * 100, 2), "%")
