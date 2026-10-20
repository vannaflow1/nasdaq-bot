"""
Black-Scholes greeks + gamma-exposure aggregation.

Math ported from the "GEX Levels [0DTE]" Pine script (the greeks in it are
correct; its open-interest model was invented and is NOT reproduced here).

THE POINT OF THIS FILE: everything works except one input. gamma_exposure()
needs REAL open interest per strike, from an options chain. Without it there
is no GEX -- any formula that manufactures OI from spot price produces levels
that track spot and carry no information. Verified: the original script's
levels sat on spot in 8/10 cases, never produced a zero-gamma crossing, and
returned "short gamma" in all 96 spot/IV/time combinations tested.

Usage when chain data exists:
    chain = pd.DataFrame(columns=["strike", "is_call", "open_interest"])
    g = gamma_exposure(chain, spot=21000, T=6.5/(365.25*24), iv=0.20)
"""
import numpy as np
import pandas as pd

SQRT_2PI = np.sqrt(2.0 * np.pi)


# ---------------------------------------------------------------- greeks
def npdf(x):
    return np.exp(-0.5 * np.square(x)) / SQRT_2PI


def ncdf(x):
    """Abramowitz-Stegun 7.1.26, ~7dp. Vectorized."""
    x = np.asarray(x, dtype=float)
    t = 1.0 / (1.0 + 0.2316419 * np.abs(x))
    d = 0.3989422804 * np.exp(-0.5 * np.square(x))
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478
        + t * (-1.821256 + t * 1.330274))))
    return np.where(x >= 0, 1.0 - p, p)


def d1_d2(S, K, T, r, sig):
    sqT = sig * np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sig * sig) * T) / sqT
    return d1, d1 - sqT


def gamma(S, K, T, r, sig):
    """d2V/dS2 — same for calls and puts."""
    d1, _ = d1_d2(S, K, T, r, sig)
    return npdf(d1) / (S * sig * np.sqrt(T))


def delta(S, K, T, r, sig, is_call=True):
    d1, _ = d1_d2(S, K, T, r, sig)
    return np.where(is_call, ncdf(d1), ncdf(d1) - 1.0)


def vanna(S, K, T, r, sig):
    """d(delta)/d(vol) — same for calls and puts."""
    d1, d2 = d1_d2(S, K, T, r, sig)
    return -npdf(d1) * d2 / (S * sig)


def charm(S, K, T, r, sig, is_call=True):
    """d(delta)/d(time) — the 0DTE decay term."""
    d1, d2 = d1_d2(S, K, T, r, sig)
    sqT = np.sqrt(T)
    c = -npdf(d1) * (2.0 * r * T - d2 * sig * sqT) / (2.0 * T * sig * sqT)
    return np.where(is_call, c, c + r * np.exp(-r * T) * ncdf(-d2))


# ------------------------------------------------------- GEX aggregation
def gamma_exposure(chain, spot, T, iv, r=0.045, multiplier=100,
                   dealer_short_calls=True):
    """Net gamma exposure per strike, in currency per 1% move.

    chain: DataFrame with columns strike, is_call, open_interest (REAL data).
           Optionally an `iv` column for per-strike vol (skew); otherwise the
           scalar `iv` is used for every strike, which is a real simplification.
    dealer_short_calls: the standard convention (dealers short calls, long
           puts). It is an ASSUMPTION about positioning, not a measurement.
           Flip it and every sign flips.
    """
    req = {"strike", "is_call", "open_interest"}
    if not req.issubset(chain.columns):
        raise ValueError(f"chain needs columns {req}, got {set(chain.columns)}")

    K = chain.strike.to_numpy(float)
    is_call = chain.is_call.to_numpy(bool)
    oi = chain.open_interest.to_numpy(float)
    sig = chain.iv.to_numpy(float) if "iv" in chain.columns else np.full_like(K, iv)

    g = gamma(spot, K, T, r, sig)
    sign = np.where(is_call, 1.0, -1.0) * (1.0 if dealer_short_calls else -1.0)
    gex = sign * g * oi * multiplier * spot * 0.01

    out = pd.DataFrame({"strike": K, "is_call": is_call,
                        "open_interest": oi, "gamma": g, "gex": gex})
    return out.groupby("strike").agg(
        gex=("gex", "sum"),
        call_gex=("gex", lambda x: x[out.loc[x.index, "is_call"]].sum()),
        put_gex=("gex", lambda x: x[~out.loc[x.index, "is_call"]].sum()),
        oi=("open_interest", "sum"),
    ).reset_index()


def key_levels(gex_by_strike, spot):
    """Call wall, put wall, zero-gamma crossing, net regime."""
    d = gex_by_strike.sort_values("strike")
    K, net = d.strike.to_numpy(), d.gex.to_numpy()

    above, below = K >= spot, K <= spot
    call_wall = K[above][np.argmax(d.call_gex.to_numpy()[above])] if above.any() else np.nan
    put_wall = K[below][np.argmin(d.put_gex.to_numpy()[below])] if below.any() else np.nan

    zero_gamma = np.nan
    for i in range(1, len(net)):
        if net[i - 1] * net[i] <= 0 and net[i - 1] != net[i]:
            w = abs(net[i - 1]) / (abs(net[i - 1]) + abs(net[i]))
            cand = K[i - 1] + (K[i] - K[i - 1]) * w
            if np.isnan(zero_gamma) or abs(cand - spot) < abs(zero_gamma - spot):
                zero_gamma = cand

    total = net.sum()
    return {"call_wall": call_wall, "put_wall": put_wall,
            "zero_gamma": zero_gamma, "total_gex": total,
            "regime": "long_gamma" if total >= 0 else "short_gamma"}


# ------------------------------------------------------------ self-check
if __name__ == "__main__":
    S, K, T, r, sig = 100.0, 100.0, 0.25, 0.045, 0.20
    print("ATM sanity check (S=K=100, T=0.25, iv=20%)")
    print(f"  delta call {float(delta(S, K, T, r, sig, True)):.4f}   (expect ~0.55)")
    print(f"  delta put  {float(delta(S, K, T, r, sig, False)):.4f}   (expect ~-0.45)")
    print(f"  gamma      {float(gamma(S, K, T, r, sig)):.5f}")
    print(f"  vanna      {float(vanna(S, K, T, r, sig)):.5f}")
    print(f"  charm call {float(charm(S, K, T, r, sig, True)):.5f}")

    # put-call parity on delta: delta_call - delta_put == 1
    err = float(delta(S, K, T, r, sig, True) - delta(S, K, T, r, sig, False)) - 1.0
    print(f"  parity error {err:.2e}  (must be ~0)")

    # ncdf against known values
    for x, want in [(0.0, 0.5), (1.0, 0.8413), (-1.96, 0.0250), (2.576, 0.9950)]:
        print(f"  ncdf({x:>6}) = {float(ncdf(x)):.4f}  expect {want}")

    print("\nDemo with FAKE flat OI — illustrates the API only, not a signal:")
    demo = pd.DataFrame({
        "strike": np.repeat(np.arange(95.0, 106.0), 2),
        "is_call": np.tile([True, False], 11),
        "open_interest": np.full(22, 1000.0),
    })
    print(" ", key_levels(gamma_exposure(demo, 100.0, T, sig), 100.0))
    print("\n>>> Replace open_interest with a real chain snapshot and this is live.")
