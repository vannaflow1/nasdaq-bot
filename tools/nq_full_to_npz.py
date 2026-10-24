"""Convert knowledge/data/nq_full/NQ_1m_<year>.parquet -> knowledge/data/nq_full/NQ_1m_<year>.npz (numpy only, so every
environment can read it). ts = minutes since 1970 (Chicago wall clock), o/h/l/c float64, v float32, sym = contract code."""
import glob, os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge", "data", "nq_full")
for f in sorted(glob.glob(os.path.join(D, "NQ_1m_*.parquet"))):
    d = pd.read_parquet(f).sort_values("ts")
    ts = (pd.to_datetime(d.ts).values.astype("datetime64[m]").astype(np.int64))
    syms = d["sym"].astype(str).to_numpy() if "sym" in d else np.array(["NQ"] * len(d))
    u, code = np.unique(syms, return_inverse=True)
    np.savez_compressed(f.replace(".parquet", ".npz"), ts=ts, o=d.open.to_numpy(float), h=d.high.to_numpy(float),
                        l=d.low.to_numpy(float), c=d.close.to_numpy(float), v=d.volume.to_numpy(np.float32), sym=code.astype(np.int16), syms=u)
    print(os.path.basename(f), len(d), d.ts.min(), d.ts.max(), len(u), "contracts")
