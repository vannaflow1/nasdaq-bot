"""om.py - the OWNER'S MODEL as rules (owner explained it 24 Oct 2026), tested like every Volta family.

His discretionary model, translated:
  1. RANGES -> composite VOLUME PROFILES over the last L full sessions (L = 5 / 20 / 60: days, weeks, months), value area
     40% (not 70%): VAH, VAL, POC are the PRIMARY levels (known before the session, from finished sessions only).
  2. A level is tradeable when CONFLUENCES line up within `tol` points at the moment price comes back to it:
       other-profile levels (another lookback's VAH/VAL/POC) | OTE 0.705 of the last swing (5- and 60-minute pivots) |
       key opens (17:00 CT daily open, NY midnight open, 08:30 CT = 9:30 NY, 09:00 CT = 10:00 NY) |
       VWAP from the NY midnight open or its +-1 / +-2 SD bands | LOW-VOLUME node of the level's profile.
     A variant needs at least `minc` distinct confluence types.
  3. ENTRY: limit order AT the level; price coming DOWN into it -> long, coming UP -> short (both directions). Filled only
     when price trades 1 tick THROUGH the level (pessimistic limit fill). One position at a time.
  4. STOP: S points (10-15, at NQ ~27,000; scaled with price for earlier years) + 1 tick slippage. TARGET: k x R, or the next primary level beyond 1.5R ("next").
  5. RISK: stop for the day after 2 losing trades (his "never lose more than ~20% in a day"); each level once a day.
  6. SESSIONS: London 02:00-07:00 CT (09:00-14:00 Lux) or New York 08:30-12:00 CT; flat by 15:00 CT.
Costs: Lucid's real MNQ commission ($1.00 round trip = 0.5 NQ points) on every trade.
Data: owner's NQ futures 1-minute, full 23-hour session, 2014 - Jan 2026 (knowledge/data/nq_full/*.npz), front contract
per day by volume; minute grid from 17:00 CT (prior evening) to 16:00 CT.
The NULL (v3, shared draws): every trade re-simulated with the side REVERSED at the same fill (same level, same minute);
one coin per session shared by every variant; 20,000 draws -> exact randomization p for the family median."""
import glob, json, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, "knowledge"); sys.path.insert(0, HERE)
NPZ = os.path.join(K, "data", "nq_full")
TICK, COMM, SLIP = 0.25, 0.5, 0.25
PRICE_REF = 27000.0                                             # stops/tolerance in "points at NQ 27,000" (his scale)
NM = 1380                                                       # minutes 17:00 CT (day before) .. 16:00 CT
def m_of(hh, mm): return ((hh * 60 + mm) - 17 * 60) % 1440      # minute index of a Chicago clock time
WIN = {"london": (m_of(2, 0), m_of(7, 0)), "ny": (m_of(8, 30), m_of(12, 0))}
FLAT = m_of(15, 0)
KEY_OPENS = [m_of(17, 0), m_of(23, 0), m_of(8, 30), m_of(9, 0)]
_DAYS = {}


# ---------------------------------------------------------------- data
def days():
    """Per trading day: O/H/L/C/V on the 1380-minute grid (float32) + dates."""
    if _DAYS: return _DAYS
    parts = []
    for f in sorted(glob.glob(os.path.join(NPZ, "NQ_1m_*.npz"))):
        z = np.load(f, allow_pickle=True)
        parts.append(pd.DataFrame({"ts": z["ts"], "o": z["o"], "h": z["h"], "l": z["l"], "c": z["c"], "v": z["v"],
                                   "sym": np.asarray(z["syms"])[z["sym"]]}))
    d = pd.concat(parts, ignore_index=True)
    t = pd.to_datetime(d.ts.values.astype("datetime64[m]"))
    mins = t.hour * 60 + t.minute
    d["day"] = (t.normalize() + pd.to_timedelta((mins >= 17 * 60).astype(int), unit="D")).date
    d["m"] = (mins - 17 * 60) % 1440
    d = d[d.m < NM]
    front = d.groupby(["day", "sym"]).v.sum().reset_index().sort_values("v").drop_duplicates("day", keep="last")
    d = d.merge(front[["day", "sym"]], on=["day", "sym"])
    d = d[pd.to_datetime(d.day).dt.weekday < 5]
    ds = sorted(d.day.unique()); n = len(ds); ix = {x: i for i, x in enumerate(ds)}
    A = {k: np.full((n, NM), np.nan, np.float32) for k in "ohlc"}; A["v"] = np.zeros((n, NM), np.float32)
    r = d.day.map(ix).to_numpy(); m = d.m.to_numpy()
    for k in "ohlcv": A[k][r, m] = d[k].to_numpy(np.float32)
    have = np.isfinite(A["c"]).sum(1)
    C = pd.DataFrame(A["c"]).ffill(axis=1).bfill(axis=1).to_numpy(np.float32)
    for k in "ohl": A[k] = np.where(np.isfinite(A[k]), A[k], C)
    A["c"] = C
    _DAYS.update(A); _DAYS["dates"] = np.array([str(x) for x in ds]); _DAYS["have"] = have
    return _DAYS


# ---------------------------------------------------------------- levels known before the session
def _bin(price): return max(0.5, round(price * 0.0001 / TICK) * TICK)


def profile(Dd, i0, i1):
    """Composite profile of sessions i0..i1-1 (typical price, volume): POC, VAH, VAL (40%), bin size, histogram."""
    tp = ((Dd["h"][i0:i1] + Dd["l"][i0:i1] + Dd["c"][i0:i1]) / 3).ravel(); v = Dd["v"][i0:i1].ravel()
    ok = np.isfinite(tp) & (v > 0)
    if ok.sum() < 200: return None
    tp, v = tp[ok], v[ok]; b = _bin(float(np.median(tp)))
    k = np.floor(tp / b).astype(np.int64); k0 = k.min(); hist = np.bincount(k - k0, weights=v)
    p = int(np.argmax(hist)); lo = hi = p; tot = hist.sum(); acc = hist[p]
    while acc < 0.40 * tot and (lo > 0 or hi < len(hist) - 1):
        up = hist[hi + 1] if hi < len(hist) - 1 else -1; dn = hist[lo - 1] if lo > 0 else -1
        if up >= dn: hi += 1; acc += up
        else: lo -= 1; acc += dn
    f = lambda j: (k0 + j + 0.5) * b
    return {"poc": f(p), "vah": (k0 + hi + 1) * b, "val": (k0 + lo) * b, "b": b, "k0": int(k0), "hist": hist,
            "mean": float(hist[hist > 0].mean())}


def is_lvn(P, price):
    j = int(np.floor(price / P["b"])) - P["k0"]
    return 0 <= j < len(P["hist"]) and P["hist"][j] < 0.5 * P["mean"]


def day_levels(Dd, i, lbs=(5, 20, 60)):
    out = {}
    for L in lbs:
        if i - L < 0: continue
        P = profile(Dd, i - L, i)
        if P: out[L] = P
    return out


# ---------------------------------------------------------------- intraday confluences (known at minute t)
def vwap_bands(Dd, i):
    h, l, c, v = Dd["h"][i], Dd["l"][i], Dd["c"][i], Dd["v"][i]; tp = (h + l + c) / 3
    s = m_of(23, 0); w = np.zeros(NM); w[s:] = v[s:]
    pv = np.cumsum(tp * w); vv = np.cumsum(w); pv2 = np.cumsum(tp * tp * w)
    vw = np.where(vv > 0, pv / np.maximum(vv, 1e-9), np.nan); sd = np.sqrt(np.maximum(pv2 / np.maximum(vv, 1e-9) - vw * vw, 0))
    vw = np.concatenate([[np.nan], vw[:-1]]); sd = np.concatenate([[np.nan], sd[:-1]])        # known BEFORE each bar
    return vw, sd


def ote_levels(Dd, i, tf):
    """At every minute: the 0.705 retracement of the last confirmed swing on tf-minute bars (pivot strength 2), or NaN.
    Known only after the pivot is confirmed (2 tf-bars later)."""
    H, L = Dd["h"][i], Dd["l"][i]; n = NM // tf
    hh = H[:n * tf].reshape(n, tf).max(1); ll = L[:n * tf].reshape(n, tf).min(1)
    out = np.full(NM, np.nan); ph = pl = None
    for j in range(2, n - 2):
        conf_t = (j + 3) * tf                                   # minute when pivot j is confirmed
        if hh[j] >= hh[j - 2:j + 3].max(): ph = (j, float(hh[j]))
        if ll[j] <= ll[j - 2:j + 3].min(): pl = (j, float(ll[j]))
        if ph and pl and conf_t < NM:
            lvl = pl[1] + 0.705 * (ph[1] - pl[1]) if ph[0] < pl[0] else ph[1] - 0.705 * (ph[1] - pl[1])
            out[conf_t:] = lvl
    return out


# ---------------------------------------------------------------- one trade
def run_trade(Dd, i, t, side, lvl, S, tgt_px, approach):
    """Filled at lvl at minute t (side +1/-1); `approach` = direction price was moving when it reached the level (-1 down,
    +1 up). Stop S points (+slippage), target price, flat 15:00 CT. Returns (R, exit minute).
    Fill bar: only the part of the bar AFTER the touch can count - i.e. its extreme in the approach direction. That is
    checked against the stop (pessimistic); a target in the fill bar is never counted."""
    H, L, C = Dd["h"][i], Dd["l"][i], Dd["c"][i]
    stop = lvl - side * S
    if -side == approach and (L[t] <= stop if side > 0 else H[t] >= stop): return (-S - SLIP - COMM) / S, t
    for u in range(t + 1, FLAT + 1):
        hs = L[u] <= stop if side > 0 else H[u] >= stop
        ht = H[u] >= tgt_px if side > 0 else L[u] <= tgt_px
        if hs: return (-S - SLIP - COMM) / S, u
        if ht: return (abs(tgt_px - lvl) - COMM) / S, u
    return (side * (C[FLAT] - lvl) - COMM) / S, FLAT


def target_px(lvl, side, S, tgt, prim):
    if tgt == "next":
        cand = sorted(p for p in prim if side * (p - lvl) >= 1.5 * S)
        if cand: return cand[0] if side > 0 else cand[-1]
        return lvl + side * 3 * S
    return lvl + side * float(tgt) * S


# ---------------------------------------------------------------- one variant on one day
def day_trades(Dd, i, var, cache):
    """All trades of variant `var` on day i. Each trade carries R (observed) and R_rev (side reversed, same fill)."""
    lev = cache["lev"].get(i)
    if lev is None: lev = cache["lev"][i] = day_levels(Dd, i)
    lbs = [L for L in var["lookbacks"] if L in lev]
    if not lbs: return []
    if i not in cache["intra"]:
        vw, sd = vwap_bands(Dd, i)
        cache["intra"][i] = {"vw": vw, "sd": sd, "ote5": ote_levels(Dd, i, 5), "ote60": ote_levels(Dd, i, 60),
                             "opens": [(m, float(Dd["o"][i][m])) for m in KEY_OPENS]}
    I = cache["intra"][i]; H, L = Dd["h"][i], Dd["l"][i]
    prim = [(Lb, nm, float(lev[Lb][nm])) for Lb in lbs for nm in ("vah", "val", "poc")]
    allprim = [p for Lb in lev for p in (lev[Lb]["vah"], lev[Lb]["val"], lev[Lb]["poc"])]
    scale = float(Dd["o"][i][m_of(17, 0)]) / PRICE_REF                # his points are for NQ ~27,000: scale with price
    w0, w1 = WIN[var["session"]]; S = float(var["stop"]) * scale; tol = float(var["tol"]) * scale
    used = set(); out = []; losses = 0; busy_until = -1
    for t in range(max(w0, 1), w1):
        if losses >= 2: break
        if t <= busy_until: continue
        for (Lb, nm, lvl) in prim:
            if (Lb, nm) in used: continue
            prev_c = Dd["c"][i][t - 1]
            if prev_c > lvl and L[t] <= lvl - TICK: side = 1                # came down into it: long
            elif prev_c < lvl and H[t] >= lvl + TICK: side = -1             # came up into it: short
            else: continue
            used.add((Lb, nm))
            conf = set()
            if any(abs(p - lvl) <= tol for Lx in lev if Lx != Lb for p in (lev[Lx]["vah"], lev[Lx]["val"], lev[Lx]["poc"])): conf.add("profile")
            for k in ("ote5", "ote60"):
                if np.isfinite(I[k][t]) and abs(I[k][t] - lvl) <= tol: conf.add("ote")
            if any(m <= t and abs(px - lvl) <= tol for m, px in I["opens"]): conf.add("open")
            vw, sd = I["vw"][t], I["sd"][t]
            if np.isfinite(vw) and any(abs(vw + z * sd - lvl) <= tol for z in (-2, -1, 0, 1, 2)): conf.add("vwap")
            if is_lvn(lev[Lb], lvl): conf.add("lvn")
            if len(conf) < var["minc"]: continue
            tp = target_px(lvl, side, S, var["tgt"], allprim)
            r, u = run_trade(Dd, i, t, side, lvl, S, tp, -side)                 # long = price came down (approach -1)
            r_rev, _ = run_trade(Dd, i, t, -side, lvl, S, target_px(lvl, -side, S, var["tgt"], allprim), -side)
            out.append({"day": i, "t": t, "side": side, "R": r, "R_rev": r_rev, "conf": len(conf)})
            losses += r < 0; busy_until = u
            break
    return out


def variant_trades(var, lo, hi, cache=None):
    Dd = days(); cache = cache if cache is not None else {"lev": {}, "intra": {}}
    idx = np.where((Dd["dates"] >= lo) & (Dd["dates"] <= hi) & (Dd["have"] > 600))[0]
    rows = []
    for i in idx: rows += day_trades(Dd, int(i), var, cache)
    return pd.DataFrame(rows, columns=["day", "t", "side", "R", "R_rev", "conf"])


# ---------------------------------------------------------------- the family
def variants(fam):
    import itertools, random
    g = fam["grid"]; keys = list(g); combos = list(itertools.product(*[g[k] for k in keys]))
    if len(combos) > 50: combos = random.Random(0).sample(combos, 50)
    return [dict(zip(keys, c)) for c in combos]


def score_family(fam, X=None, S=None, reps=None):
    """families.py hook (engine 'owner_model'): validation 2022-now, search 2014-21, alpha from the fast slots."""
    import families as FA, sealed as SE
    res, R, V = score(fam); L = FA.ledger(); j, alpha = FA._alpha_for(fam, L, SE)
    if "verdict" in res: return res, R, V
    passed = res["median_edge_B"] > 0 and res["share_positive_B"] >= 0.6 and res["p"] < alpha
    res.update({"families_scored": len(L) + 1, "alpha": alpha, "passed": bool(passed), "rules": "v2", "epoch": fam.get("epoch", ""),
                "null": "v3-sign-flip-shared"})
    return res, R, V


def score(fam, lo_a="2014-01-01", hi_a="2021-12-31", lo_b="2022-01-01", hi_b="2099-12-31", draws=20000, seed=7):
    """Family statistic: median over variants of mean R on validation; null v3 (side reversed, one coin per session
    shared by all variants), exact randomization p. Search-year stats pick the forward variant."""
    V = variants(fam); cache = {"lev": {}, "intra": {}}; rows = []; TB = []
    for v in V:
        TA = variant_trades(v, lo_a, hi_a, cache); Tb = variant_trades(v, lo_b, hi_b, cache); TB.append(Tb)
        rows.append({"params": json.dumps(v), "n_A": len(TA), "edge_A": float(TA.R.mean()) if len(TA) else np.nan,
                     "n_B": len(Tb), "edge_B": float(Tb.R.mean()) if len(Tb) else np.nan,
                     "lb10_A": float(np.quantile([TA.R.sample(len(TA), replace=True, random_state=s).mean() for s in range(200)], 0.1)) if len(TA) >= 20 else np.nan})
    R = pd.DataFrame(rows); ok = [j for j in range(len(V)) if R.n_B[j] >= 20]
    if len(ok) < 5: return {"verdict": "TOO FEW TRADES", "usable": len(ok)}, R, V
    med = float(np.median([R.edge_B[j] for j in ok])); share = float(np.mean([R.edge_B[j] > 0 for j in ok]))
    days_all = sorted(set().union(*[set(TB[j].day) for j in ok])); dpos = {d: k for k, d in enumerate(days_all)}
    rng = np.random.default_rng(seed); null = np.empty(draws)
    mats = [(np.array([dpos[d] for d in TB[j].day]), TB[j].R.to_numpy(), TB[j].R_rev.to_numpy()) for j in ok]
    for b in range(draws):
        flip = rng.random(len(days_all)) < 0.5
        null[b] = np.median([np.where(flip[di], rr, ro).mean() for di, ro, rr in mats])
    p = float((1 + (null >= med).sum()) / (1 + draws))
    return {"variants": len(V), "usable": len(ok), "median_edge_A": round(float(np.nanmedian(R.edge_A)), 4),
            "median_edge_B": round(med, 4), "share_positive_B": round(share, 3), "placebo_median_mean": round(float(null.mean()), 4),
            "p": round(p, 5)}, R, V


if __name__ == "__main__":
    D = days(); print(len(D["dates"]), D["dates"][0], D["dates"][-1])
