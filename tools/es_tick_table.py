"""Adds ES + NYSE TICK columns to Volta's session table (same session/date alignment as NQ).
k_ = known at the 08:30 CT open, y_ = outcomes of the NY session. TICK file = NYSE TICK + 10000, 5-min bars, ET."""
import pandas as pd, numpy as np
P = "/home/claude/nasdaq-bot/knowledge/session_table.csv"
T = pd.read_csv(P, parse_dates=["date"])
T = T[[c for c in T if not (c.startswith(("k_es_", "y_es_", "k_tick_", "y_tick_", "k_smt_", "y_nq_minus_es", "k_nq_minus_es")))]]
def sessions(df):
    df = df.copy(); df["sess"] = df.ts.dt.normalize() + pd.to_timedelta((df.ts.dt.hour >= 17).astype(int), unit="D")
    df["m"] = df.ts.dt.hour * 60 + df.ts.dt.minute; return df
def feats(df, tag):
    out = {}
    for s, g in df.groupby("sess"):
        if g.Symbol.nunique() > 1 or len(g) < 900: continue
        on = g[(g.m >= 17 * 60) | (g.m < 510)]; ny = g[(g.m >= 510) & (g.m < 900)]
        asia = g[(g.m >= 18 * 60) | (g.m < 120)]; pre = g[(g.m >= 120) & (g.m < 510)]
        if len(ny) < 350 or len(on) < 300 or len(asia) < 200: continue
        o, c = float(ny.Open.iloc[0]), float(ny.Close.iloc[-1])
        out[s] = dict(o=o, c=c, hi=float(ny.High.max()), lo=float(ny.Low.min()), oh=float(on.High.max()), ol=float(on.Low.min()),
                      on_open=float(on.Open.iloc[0]), ah=float(asia.High.max()), al=float(asia.Low.min()),
                      pre_hi=float(pre.High.max()), pre_lo=float(pre.Low.min()))
    return pd.DataFrame(out).T
E = feats(sessions(pd.read_pickle("es1m.pkl")), "es"); N = feats(sessions(pd.read_pickle("nq1m.pkl")), "nq")
E["pc"], E["ph"], E["pl"] = E.c.shift(1), E.hi.shift(1), E.lo.shift(1)
R = pd.DataFrame(index=E.index)
R["k_es_on_range"] = (E.oh - E.ol) / E.o * 100
R["k_es_gap"] = (E.o - E.pc) / E.pc * 100
R["k_es_on_return"] = (E.o / E.on_open - 1) * 100
R["k_es_open_vs_yday"] = (E.o - E.pl) / (E.ph - E.pl).clip(lower=1e-9)
J = N.join(E, rsuffix="_e", how="inner")
R["k_nq_minus_es_on"] = ((J.o / J.on_open - 1) - (J.o_e / J.on_open_e - 1)) * 100
# SMT divergence before the open: one index took its Asia high (low) in London/pre-market, the other didn't
nqh, esh = (J.pre_hi > J.ah).astype(float), (J.pre_hi_e > J.ah_e).astype(float)
nql, esl = (J.pre_lo < J.al).astype(float), (J.pre_lo_e < J.al_e).astype(float)
R["k_smt_high"] = (nqh != esh).astype(float); R["k_smt_high_nq_only"] = ((nqh == 1) & (esh == 0)).astype(float)
R["k_smt_low"] = (nql != esl).astype(float); R["k_smt_low_nq_only"] = ((nql == 1) & (esl == 0)).astype(float)
R["y_es_range"] = (E.hi - E.lo) / E.o * 100
R["y_es_return"] = (E.c / E.o - 1) * 100
R["y_es_took_yday_high"] = (E.hi > E.ph).astype(float).where(E.ph.notna())
R["y_es_took_yday_low"] = (E.lo < E.pl).astype(float).where(E.pl.notna())
R["y_nq_minus_es"] = ((J.c / J.o - 1) - (J.c_e / J.o_e - 1)) * 100
# NYSE TICK (ET; RTH 09:30-16:00 ET = 08:30-15:00 CT)
t = pd.read_pickle("tick5m.pkl"); t = t[(t.ts.dt.hour * 60 + t.ts.dt.minute).between(570, 960)]
for c in ("Open", "High", "Low", "Close"): t[c] = t[c] - 10000
t = t[(t.High.abs() < 3000) & (t.Low.abs() < 3000)]
g = t.groupby(t.ts.dt.normalize())
TK = pd.DataFrame({"y_tick_mean": g.Close.mean(), "y_tick_max": g.High.max(), "y_tick_min": g.Low.min(),
                   "y_tick_ext_up": g.High.apply(lambda x: (x >= 1000).sum()), "y_tick_ext_dn": g.Low.apply(lambda x: (x <= -1000).sum()),
                   "y_tick_first30_mean": t[(t.ts.dt.hour * 60 + t.ts.dt.minute) <= 600].groupby(t.ts.dt.normalize()).Close.mean(),
                   "n": g.size()})
TK = TK[TK.n >= 60].drop(columns="n")
for a, b in (("mean", "k_tick_yday_mean"), ("max", "k_tick_yday_max"), ("min", "k_tick_yday_min"),
             ("ext_up", "k_tick_yday_ext_up"), ("ext_dn", "k_tick_yday_ext_dn")):
    TK[b] = TK["y_tick_" + a].shift(1)
TK["k_tick_mean5"] = TK.y_tick_mean.shift(1).rolling(5).mean()
R = R.join(TK, how="left")
R.index = pd.DatetimeIndex(R.index).strftime("%Y-%m-%d"); R.index.name = "session"
T = T.merge(R.round(4).reset_index(), on="session", how="left")
T.to_csv(P, index=False, float_format="%.5g")
new = [c for c in R.columns]
print(T.shape, "new cols", len(new)); print(T[new].notna().mean().round(2).to_dict())
print("SMT high freq", T.k_smt_high.mean().round(3), "| corr y_return vs y_es_return", T.y_return.corr(T.y_es_return).round(3))
print("TICK mean vs NQ return corr", T.y_tick_mean.corr(T.y_return).round(3))
