"""Intraday tests on the minute table: does first-hour options flow / 0DTE pricing tell us about the rest of the day?"""
import glob, numpy as np, pandas as pd
M = pd.concat([pd.read_csv(f, parse_dates=["ts"]) for f in sorted(glob.glob("/home/claude/spxdata/minutes_*.csv"))], ignore_index=True)
M["d"] = M.ts.dt.normalize(); M["hm"] = M.ts.dt.hour * 100 + M.ts.dt.minute
cols = [c for c in M if c.startswith(("buy_", "sell_")) and "prem" not in c]
M[cols] = M[cols].fillna(0)
def net(df, key): return df[[c for c in cols if c.startswith("buy_") and key in c]].sum(1) - df[[c for c in cols if c.startswith("sell_") and key in c]].sum(1)
rows = []
for d, g in M.groupby("d"):
    g = g.set_index("hm")
    if 1030 not in g.index or 1600 not in g.index or 931 not in g.index: continue
    h1 = g.loc[931:1030]
    r = {"d": d, "spx_open": g.at[931, "spx"], "spx_1030": g.at[1030, "spx"], "spx_close": g.at[1600, "spx"],
         "hi_rest": g.loc[1031:1600, "spx"].max(), "lo_rest": g.loc[1031:1600, "spx"].min(),
         "hi_day": g.spx.max(), "lo_day": g.spx.min(),
         "h1_net_calls_0": net(h1, "d0_c").sum(), "h1_net_puts_0": net(h1, "d0_p").sum(),
         "h1_net_calls_all": net(h1, "_c_").sum(), "h1_net_puts_all": net(h1, "_p_").sum(),
         "h1_net_otm_calls_0": net(h1, "d0_c_otm").sum(), "h1_net_otm_puts_0": net(h1, "d0_p_otm").sum(),
         "h1_netprem": (h1.buy_prem - h1.sell_prem).sum() / 1e6,
         "e1_dte": g.at[1030, "e1_dte"] if "e1_dte" in g else np.nan,
         "strad_open": g.at[945, "e1_straddle"] if 945 in g.index else np.nan, "strad_1030": g.at[1030, "e1_straddle"],
         "vix_open": g.loc[931:940, "vix"].dropna().iloc[0] if g.loc[931:940, "vix"].notna().any() else np.nan, "vix_1030": g.at[1030, "vix"],
         "vvix_open": g.loc[931:940, "vvix"].dropna().iloc[0] if g.loc[931:940, "vvix"].notna().any() else np.nan, "vvix_1030": g.at[1030, "vvix"],
         "total_vol_h1": h1[cols].sum().sum()}
    rows.append(r)
R = pd.DataFrame(rows).set_index("d")
R["ret_h1"] = (R.spx_1030 / R.spx_open - 1) * 100
R["ret_rest"] = (R.spx_close / R.spx_1030 - 1) * 100
R["rng_rest"] = (R.hi_rest - R.lo_rest) / R.spx_1030 * 100
R["call_put_tilt_0"] = (R.h1_net_calls_0 - R.h1_net_puts_0) / R.total_vol_h1.clip(lower=1)
R["call_put_tilt_all"] = (R.h1_net_calls_all - R.h1_net_puts_all) / R.total_vol_h1.clip(lower=1)
R["otm_tilt_0"] = (R.h1_net_otm_calls_0 - R.h1_net_otm_puts_0) / R.total_vol_h1.clip(lower=1)
R["vix_chg_h1"] = R.vix_1030 / R.vix_open - 1; R["vvix_chg_h1"] = R.vvix_1030 / R.vvix_open - 1
R["strad_rest_ratio"] = R.rng_rest / (R.strad_1030 / R.spx_1030 * 100)          # realized rest-of-day range vs 0DTE straddle
R.to_csv("/home/claude/brain/spx_intraday_daily.csv")
yrs = R.index.year
def test(x, y, name):
    D = pd.DataFrame({"x": R[x], "y": R[y], "yr": yrs}).dropna()
    by = D.groupby("yr").apply(lambda g: g.x.corr(g.y))
    q = pd.qcut(D.x.rank(method="first"), 5, labels=False); ym = D.groupby(q).y.mean()
    print(f"{name:62s} corr {D.x.corr(D.y):+.3f} | same sign {int((np.sign(by) == np.sign(D.x.corr(D.y))).sum())}/{len(by)} yrs "
          f"| bottom fifth {ym.iloc[0]:+.3f} top fifth {ym.iloc[-1]:+.3f} | 2024+ corr {D[D.yr >= 2024].x.corr(D[D.yr >= 2024].y):+.3f}")
print(len(R), "days")
test("call_put_tilt_0", "ret_rest", "1st-hour 0DTE net call-minus-put buying -> rest-of-day return")
test("call_put_tilt_all", "ret_rest", "1st-hour all-expiry call-put tilt -> rest-of-day return")
test("otm_tilt_0", "ret_rest", "1st-hour 0DTE OTM call-put tilt -> rest-of-day return")
test("h1_netprem", "ret_rest", "1st-hour customer net premium -> rest-of-day return")
test("ret_h1", "ret_rest", "(control) 1st-hour return -> rest-of-day return")
test("vix_chg_h1", "ret_rest", "1st-hour VIX change -> rest-of-day return")
test("vvix_chg_h1", "rng_rest", "1st-hour VVIX change -> rest-of-day range")
test("vix_chg_h1", "rng_rest", "1st-hour VIX change -> rest-of-day range")
test("total_vol_h1", "rng_rest", "1st-hour option volume -> rest-of-day range")
print("0DTE straddle at 10:30 vs realized rest-of-day range: median ratio", R.strad_rest_ratio.median().round(3),
      "by year", R.strad_rest_ratio.groupby(yrs).median().round(2).to_dict())
