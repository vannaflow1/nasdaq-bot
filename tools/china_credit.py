"""China credit impulse vs Nasdaq: does China's credit cycle lead NQ by ~6-12 months?
Credit: BIS 'credit to the private non-financial sector, China' (quarterly, via FRED). Impulse = change in the 12-month
credit FLOW, scaled by the credit stock a year earlier (the standard credit-impulse construction).
Nasdaq: ^NDX monthly closes (Yahoo). Tests: correlation of the impulse with the NEXT 3/6/9/12 months of NDX returns,
by decade, plus a simple rule (long when the impulse is rising) vs buy-and-hold."""
import io, json, os, urllib.request
import numpy as np, pandas as pd
os.makedirs("knowledge/research_out", exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
def fred(sid):
    raw = urllib.request.urlopen(urllib.request.Request(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=UA), timeout=120).read().decode()
    d = pd.read_csv(io.StringIO(raw)); d.columns = ["date", "v"]; d["date"] = pd.to_datetime(d.date)
    return d.set_index("date").v.replace(".", np.nan).astype(float).dropna()
out = []
def dbnomics(code):
    u = f"https://api.db.nomics.world/v22/series/{code}?observations=1&format=json"
    j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read())
    d = j["series"]["docs"][0]
    return pd.Series(pd.to_numeric(pd.Series(d["value"]), errors="coerce").values, index=pd.PeriodIndex(d["period"], freq="Q").to_timestamp(how="end").normalize()).dropna()
credit = None; used = None
for name, fn in (("DBnomics BIS/WS_TC/Q.CN.P.A.M.XDC.A (credit to private non-fin. sector, CNY)", lambda: dbnomics("BIS/WS_TC/Q.CN.P.A.M.XDC.A")),
                 ("DBnomics BIS/WS_TC/Q.CN.P.B.M.XDC.A (bank credit)", lambda: dbnomics("BIS/WS_TC/Q.CN.P.B.M.XDC.A")),
                 ("FRED CRDQCNAPABIS", lambda: fred("CRDQCNAPABIS"))):
    try:
        s = fn(); out.append(f"{name}: {len(s)} obs {s.index[0].date()} -> {s.index[-1].date()}, last {s.iloc[-1]:,.0f}")
        if credit is None and len(s) > 60: credit = s; used = name
    except Exception as e:
        out.append(f"{name}: failed {type(e).__name__} {str(e)[:80]}")
u = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENDX?interval=1mo&period1=631152000&period2=1800000000"
r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["chart"]["result"][0]
ndx = pd.Series(r["indicators"]["quote"][0]["close"], index=pd.to_datetime(r["timestamp"], unit="s")).dropna()
ndx = ndx.resample("ME").last()
out.append(f"NDX monthly: {len(ndx)} obs {ndx.index[0].date()} -> {ndx.index[-1].date()}")
if credit is not None:
    q = credit.resample("QE").last()
    if "percent" in used.lower() or used == "QCNPAM770A": pass
    flow = q - q.shift(4)                              # credit created over the past 12 months
    imp = (flow - flow.shift(4)) / q.shift(4) * 100    # change in that flow vs a year ago, % of the old stock
    imp_m = imp.resample("ME").ffill()
    # data is published ~3 months after the quarter: only use it with that delay
    avail = imp_m.shift(3)
    res = []
    for h in (3, 6, 9, 12):
        fwd = (ndx.shift(-h) / ndx - 1) * 100
        D = pd.DataFrame({"x": avail, "y": fwd}).dropna()
        D = D[D.index >= "2000-01-01"]
        c = D.x.corr(D.y)
        by = {f"{a}-{b}": round(D[(D.index.year >= a) & (D.index.year <= b)].x.corr(D[(D.index.year >= a) & (D.index.year <= b)].y), 2)
              for a, b in ((2000, 2009), (2010, 2017), (2018, 2026))}
        res.append(f"impulse (as published) vs next {h:2d} months of NDX: corr {c:+.2f} over {len(D)} months (~{len(D)//h} independent) | by period {by}")
        D2 = pd.DataFrame({"x": imp_m, "y": fwd}).dropna(); D2 = D2[D2.index >= "2000-01-01"]
        res.append(f"   (if known instantly, impossible in reality: corr {D2.x.corr(D2.y):+.2f})")
    out += res
    m = (ndx.pct_change().shift(-1)).dropna()
    rising = (avail.diff(3) > 0).reindex(m.index).fillna(False)
    sub = m[m.index >= "2000-01-01"]; ri = rising.reindex(sub.index).fillna(False)
    out.append(f"Rule 'long NDX only while the published impulse rose over the last 3 months' 2000-2026: avg monthly {sub[ri].mean()*100:+.2f}% "
               f"in {ri.sum()} months vs {sub[~ri].mean()*100:+.2f}% in the other {(~ri).sum()} months (buy&hold {sub.mean()*100:+.2f}%)")
    for a, b in ((2000, 2009), (2010, 2017), (2018, 2026)):
        s2 = sub[(sub.index.year >= a) & (sub.index.year <= b)]; r2 = ri.reindex(s2.index)
        out.append(f"   {a}-{b}: rising {s2[r2].mean()*100:+.2f}%/month vs not {s2[~r2].mean()*100:+.2f}%/month")
    pd.DataFrame({"impulse": imp}).to_csv("knowledge/research_out/china_credit_impulse.csv")
open("knowledge/research_out/china_credit.txt", "w").write("\n".join(out)); print("\n".join(out))
