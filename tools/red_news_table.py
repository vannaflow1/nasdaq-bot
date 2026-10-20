"""Red-folder (high-impact) US events 2014+ -> session-table columns known BEFORE the 08:30 CT NY open.
k_red_any / k_red_premarket (released before the open, e.g. CPI, NFP 08:30 ET) / k_red_session (10:00 ET+) / k_fomc_day /
k_red_count, and for pre-open releases the standardised SURPRISE (actual - forecast, z-scored per event on past data;
sign flipped for jobless claims so that + = stronger economy everywhere)."""
import numpy as np, pandas as pd
E = pd.read_csv("knowledge/data/econ_events_red.csv", parse_dates=["release_ts_utc"])
E = E[(E.release_ts_utc >= "2013-01-01") & (~E.date_is_estimated.astype(bool))].copy()
E["et"] = E.release_ts_utc.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None)
E["session"] = E.et.dt.strftime("%Y-%m-%d"); E["hm"] = E.et.dt.hour * 60 + E.et.dt.minute
E["raw"] = (pd.to_numeric(E.actual, errors="coerce") - pd.to_numeric(E.forecast, errors="coerce"))
E.loc[E.event == "jobless_claims", "raw"] *= -1
E = E.sort_values("et")
E["z"] = E.groupby("event").raw.transform(lambda s: (s - s.expanding(20).mean().shift(1)) / s.expanding(20).std().shift(1)).clip(-4, 4)
pre = E[E.hm < 9 * 60 + 30]; ses = E[(E.hm >= 9 * 60 + 30) & (E.hm < 16 * 60)]
out = pd.DataFrame({"k_red_any": E[E.hm < 16 * 60].groupby("session").size().clip(upper=1),
                    "k_red_count": E[E.hm < 16 * 60].groupby("session").size(),
                    "k_red_premarket": pre.groupby("session").size().clip(upper=1),
                    "k_red_session": ses.groupby("session").size().clip(upper=1),
                    "k_fomc_day": E[E.event == "fomc"].groupby("session").size().clip(upper=1),
                    "k_red_surprise": pre.groupby("session").z.sum(min_count=1),
                    "k_cpi_surprise": pre[pre.event == "cpi"].groupby("session").z.sum(min_count=1),
                    "k_nfp_surprise": pre[pre.event == "nonfarm_payrolls"].groupby("session").z.sum(min_count=1)})
P = "knowledge/session_table.csv"; T = pd.read_csv(P)
T = T.drop(columns=[c for c in out.columns if c in T]).merge(out.reset_index().rename(columns={"index": "session"}), on="session", how="left")
for c in ("k_red_any", "k_red_count", "k_red_premarket", "k_red_session", "k_fomc_day"):
    T[c] = T[c].fillna(0).where(T.session >= "2013-02-01")
T.to_csv(P, index=False, float_format="%.5g")
print(T[["k_red_any", "k_red_premarket", "k_red_session", "k_fomc_day"]].mean().round(3).to_dict(), "surprise days", T.k_red_surprise.notna().sum())
