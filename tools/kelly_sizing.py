"""tools/kelly_sizing.py - how much to risk per trade on a forward family, given how unsure the edge still is (report only)

Kelly (1956) gives the growth-optimal fraction f* = mu / sigma^2 when the edge mu per trade (in R) and the per-trade
spread sigma (in R) are KNOWN. Volta only has a posterior for mu (families.json -> forward.posterior_mean / _sd, from
the frozen design's prior + validation + forward trades). With growth g(f) = f*mu - f^2*sigma^2/2 per trade (small-edge
approximation), averaging over the posterior gives the same optimum at the posterior mean, but the downside is real:
if mu is at its 10th percentile, any f above 2*mu10/sigma^2 shrinks capital. So this reports:
  kelly       = m / sigma^2            fraction of capital to lose on a -1R trade (growth-optimal on average)
  half, quarter                        the usual haircuts for estimation error (MacLean, Thorp & Ziemba)
  p_edge_neg  = P(mu < 0)
  safe_at_90  = 2*mu10/sigma^2 if mu10 > 0 else 0   (largest f whose growth is positive even at the 10th percentile)
sigma = the per-trade sd the frozen design uses for conditional power (cp_sd_per_trade_R), never re-estimated here.
Prop accounts are NOT Kelly problems (fixed fee, drawdown floor, payout cap): use the prop simulator for those.
Nothing here changes a gate, a forward design or eta's inputs.
Run: python tools/kelly_sizing.py   -> knowledge/research_out/sizing.json"""
import json, os
from statistics import NormalDist

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = os.path.join(HERE, "knowledge")


def size(m, s, sigma):
    N = NormalDist()
    mu10 = m - 1.2816 * s
    k = m / sigma ** 2
    return {"posterior_mean_R": round(m, 4), "posterior_sd_R": round(s, 4), "sigma_R": sigma,
            "p_edge_neg": round(N.cdf(-m / s), 3) if s > 0 else None,
            "kelly": round(k, 4), "half_kelly": round(k / 2, 4), "quarter_kelly": round(k / 4, 4),
            "safe_at_90": round(max(0.0, 2 * mu10 / sigma ** 2), 4),
            "expected_R_per_100_trades": round(100 * m, 1), "sd_R_per_100_trades": round(10 * sigma, 1)}


def run():
    fams = json.load(open(os.path.join(K, "families.json")))
    out = {}
    for f in fams:
        fw = f.get("forward") or {}
        if f.get("status") != "forward" or fw.get("posterior_mean") is None: continue
        try:
            d = json.load(open(os.path.join(K, "frozen", f"{f['id']}_forward_design.json")))
            sigma = float(d["futility"]["cp_sd_per_trade_R"])
        except Exception:
            continue
        r = size(float(fw["posterior_mean"]), float(fw.get("posterior_sd") or 0.0), sigma)
        r.update({"forward_trades": fw.get("n"), "as_of": fw.get("date")})
        out[f["id"]] = r
    res = {"what": "Fractional-Kelly risk per trade (share of capital lost on a -1R trade) from each forward family's "
                   "posterior edge. Report only; prop accounts are sized by the prop simulator, not by this.",
           "families": out}
    json.dump(res, open(os.path.join(K, "research_out", "sizing.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    for k, v in run()["families"].items():
        print(f"{k}: mean {v['posterior_mean_R']:+.4f}R sd {v['posterior_sd_R']:.4f} P(edge<0)={v['p_edge_neg']} | "
              f"kelly {v['kelly']:.2%} half {v['half_kelly']:.2%} quarter {v['quarter_kelly']:.2%} "
              f"safe@90 {v['safe_at_90']:.2%} | n={v['forward_trades']}")
