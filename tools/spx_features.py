"""SPX options (the owner's ThetaData extract) -> daily dealer-positioning features + intraday flow tests.
Greeks: Black-Scholes on the 09:35 mid (r=0, SPXW PM settlement at 16:00 ET)."""
import glob, sys, numpy as np, pandas as pd
from math import sqrt
D = "/home/claude/spxdata/"
N = lambda x: 0.5 * (1 + np.vectorize(__import__("math").erf)(x / sqrt(2)))
from scipy.stats import norm
def bs_price(S, K, T, v, call):
    d1 = (np.log(S / K) + 0.5 * v * v * T) / (v * np.sqrt(T)); d2 = d1 - v * np.sqrt(T)
    return np.where(call, S * norm.cdf(d1) - K * norm.cdf(d2), K * norm.cdf(-d2) - S * norm.cdf(-d1))
def implied_vol(P, S, K, T, call):
    lo, hi = np.full(P.shape, 0.01), np.full(P.shape, 4.0)
    intrinsic = np.where(call, np.maximum(S - K, 0), np.maximum(K - S, 0))
    ok = (P > intrinsic + 0.01) & (T > 0)
    for _ in range(45):
        mid = (lo + hi) / 2; pm = bs_price(S, K, T, mid, call)
        hi = np.where(pm > P, mid, hi); lo = np.where(pm > P, lo, mid)
    return np.where(ok, (lo + hi) / 2, np.nan)
def gamma(S, K, T, v):
    d1 = (np.log(S / K) + 0.5 * v * v * T) / (v * np.sqrt(T)); return norm.pdf(d1) / (S * v * np.sqrt(T))

def day_features(C):
    """C = one year of the contracts table. Returns one row per day."""
    C = C.copy()
    C["call"] = C.right.eq("CALL")
    # minutes from 09:35 to expiry 16:00 ET, in years (trading-time-ish: calendar minutes)
    C["T"] = ((C.exp - C.date).dt.days * 1440 + (16 * 60 - (9 * 60 + 35))) / (365 * 1440)
    S, K = C.spx_0935.values, C.strike.values
    C["iv"] = implied_vol(C.mid_0935.values, S, K, C["T"].values, C.call.values)
    # fill missing IV with that day's ATM-ish median per expiry (deep wings with no quote)
    C["iv"] = C.groupby(["date", "exp"]).iv.transform(lambda x: x.fillna(x.median()))
    C["g"] = gamma(S, K, C["T"].values, C.iv.values) * S * S * 0.01 * 100         # $ gamma per 1% move per contract
    C["net_cust"] = (C.buy.fillna(0) - C.sell.fillna(0))                              # customers' net buying today
    return C

if __name__ == "__main__" and "--build" not in sys.argv:
    for f in sorted(glob.glob(D + "contracts_*.csv"))[:1]:
        C = pd.read_csv(f, parse_dates=["date", "exp"]); X = day_features(C)
        print(X.iv.describe()); print(X[(X.date == X.date.iloc[0]) & (X.dte == 0)].sort_values("g", ascending=False).head(5)[["strike", "right", "mid_0935", "spx_0935", "iv", "g", "open_interest"]])

def build(years=None):
    files = sorted(glob.glob(D + "contracts_*.csv"))
    C = pd.concat([pd.read_csv(f, parse_dates=["date", "exp"]) for f in files], ignore_index=True)
    C["call"] = C.right.eq("CALL")
    days = sorted(C.date.unique()); prev = dict(zip(days[1:], days[:-1]))
    # yesterday-close IV per contract (known before today's open)
    P = C[["date", "exp", "strike", "right", "mid_1550", "spx_1550", "call"]].copy()
    P["T"] = ((P.exp - P.date).dt.days * 1440 + 10) / (365 * 1440)
    P["iv_y"] = implied_vol(P.mid_1550.values, P.spx_1550.values, P.strike.values, P["T"].values, P.call.values)
    P["date"] = P.date.map(lambda d: next_day.get(d, pd.NaT)) if False else P.date
    nxt = dict(zip(days[:-1], days[1:])); P["date"] = P.date.map(nxt)
    P = P.dropna(subset=["date"])[["date", "exp", "strike", "right", "iv_y", "spx_1550"]].rename(columns={"spx_1550": "spot_y"})
    X = C.merge(P, on=["date", "exp", "strike", "right"], how="left")
    X["spot_y"] = X.groupby("date").spot_y.transform("max")
    X["iv_y"] = X.groupby(["date", "exp"]).iv_y.transform(lambda s: s.fillna(s.median()))
    X["T0"] = ((X.exp - X.date).dt.days * 1440 + 390) / (365 * 1440)              # from 09:30 to 16:00 expiry
    # customers' cumulative net buying BEFORE today, per contract (dealer holds the other side)
    X = X.sort_values(["exp", "strike", "right", "date"])
    X["net"] = X.buy.fillna(0) - X.sell.fillna(0)
    X["cum_prev"] = X.groupby(["exp", "strike", "right"]).net.transform(lambda s: s.cumsum().shift(1).fillna(0))
    rows = []
    for d, g in X.groupby("date"):
        S = g.spot_y.iloc[0]
        if not np.isfinite(S) or g.iv_y.notna().sum() < 20: continue
        g = g[g.iv_y.notna()]
        sgn = np.where(g.call, 1.0, -1.0); oi = g.open_interest.fillna(0).values
        def gex_at(spot, w, mask=None):
            gm = gamma(spot, g.strike.values, g.T0.values, g.iv_y.values) * spot * spot * 0.01 * 100
            v = w * gm; return np.nansum(v if mask is None else v[mask])
        z0 = (g.dte == 0).values
        r = {"date": d, "spot": S}
        r["gex_oi"] = gex_at(S, sgn * oi) / 1e9                                    # classic: dealers long calls / short puts
        r["gex_oi_0dte"] = gex_at(S, sgn * oi, z0) / 1e9
        r["gex_flow"] = gex_at(S, -g.cum_prev.values) / 1e9                        # from real customer flow (since 7 DTE)
        r["gex_flow_0dte"] = gex_at(S, -g.cum_prev.values, z0) / 1e9
        r["oi_0dte_share"] = oi[z0].sum() / max(oi.sum(), 1)
        r["pcr_oi"] = oi[~g.call.values].sum() / max(oi[g.call.values].sum(), 1)
        # flip level: where classic GEX changes sign on a +-4% grid
        grid = S * (1 + np.linspace(-0.04, 0.04, 33)); vals = np.array([gex_at(s, sgn * oi) for s in grid])
        sc = np.where(np.diff(np.sign(vals)) != 0)[0]
        r["flip_dist"] = ((grid[sc[np.abs(grid[sc] - S).argmin()]] / S - 1) * 100) if len(sc) else (4.0 if vals[16] > 0 else -4.0)
        # walls: biggest call-gamma strike above, put-gamma strike below
        gm = gamma(S, g.strike.values, g.T0.values, g.iv_y.values) * oi
        near = np.abs(g.strike.values / S - 1) <= 0.03                             # walls within 3% of spot
        up = g.call.values & (g.strike.values > S) & near; dn = (~g.call.values) & (g.strike.values < S) & near
        r["call_wall_dist"] = (g.strike.values[up][gm[up].argmax()] / S - 1) * 100 if up.any() else np.nan
        r["put_wall_dist"] = (g.strike.values[dn][gm[dn].argmax()] / S - 1) * 100 if dn.any() else np.nan
        # nearest-expiry ATM IV at yesterday's close
        e = g[g.exp == g.exp.min()]; r["iv_near_atm"] = e.iloc[(e.strike - S).abs().argsort()[:4]].iv_y.mean()
        rows.append(r)
    F = pd.DataFrame(rows).set_index("date")
    # yesterday's customer flow (known at today's open)
    Y = C.assign(net=C.buy.fillna(0) - C.sell.fillna(0), netp=C.buy_prem.fillna(0) - C.sell_prem.fillna(0))
    fl = pd.DataFrame({
        "cust_net_prem": Y.groupby("date").netp.sum() / 1e6,
        "cust_net_calls_0dte": Y[(Y.dte == 0) & Y.call].groupby("date").net.sum(),
        "cust_net_puts_0dte": Y[(Y.dte == 0) & ~Y.call].groupby("date").net.sum(),
        "volume": Y.groupby("date").volume.sum(),
        "put_call_vol": Y[~Y.call].groupby("date").volume.sum() / Y[Y.call].groupby("date").volume.sum()})
    fl.index = fl.index.map(nxt); fl = fl[fl.index.notna()].add_suffix("_yday")
    return F.join(fl, how="left")

if __name__ == "__main__" and "--build" in sys.argv:
    import time; t = time.time(); F = build(); print(F.shape, round(time.time() - t)); print(F.describe().T.round(3))
    F.to_csv("/home/claude/brain/spx_daily_feats.csv")
