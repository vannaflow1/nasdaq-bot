"""Volta - futures tick extractor (Sierra Chart .scid inside the downloaded zip parts). Runs on your PC.
Reads every CL-*.zip and GC-*.zip in this folder WITHOUT unzipping, turns each contract's ticks into 1-minute bars
(open/high/low/close, volume, buy volume = trades at the ask, sell volume = trades at the bid), then joins the
contracts into one continuous series per market (each day uses the contract with the most volume = the front month).
Output: volta_out/CL_1m.parquet and volta_out/GC_1m.parquet (Chicago time, like the NQ data). Nothing is changed.
Run again any time: finished contracts are cached in volta_out/contracts/."""
import glob, os, re, sys, time, zipfile
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "volta_out"); CACHE = os.path.join(OUT, "contracts")
REC = np.dtype([("t", "<i8"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"),
                ("n", "<u4"), ("v", "<u4"), ("bv", "<u4"), ("av", "<u4")])
EPOCH = np.datetime64("1899-12-30T00:00:00", "us")


def bars_from_scid(raw):
    """raw bytes of one .scid file -> 1-minute bars in Chicago time."""
    if raw[:4] != b"SCID": return None
    hdr = int.from_bytes(raw[4:8], "little")
    r = np.frombuffer(raw, dtype=REC, offset=hdr, count=(len(raw) - hdr) // REC.itemsize)
    if len(r) == 0: return None
    px = r["c"].astype(np.float64); ok = np.isfinite(px) & (px > 0)
    r = r[ok]; px = px[ok]
    ts = EPOCH + r["t"].astype("timedelta64[us]")
    t = pd.DatetimeIndex(ts).tz_localize("UTC").tz_convert("America/Chicago").tz_localize(None).floor("1min")
    df = pd.DataFrame({"t": t, "p": px, "v": r["v"].astype(np.int64), "buy": r["av"].astype(np.int64), "sell": r["bv"].astype(np.int64)})
    g = df.groupby("t")
    b = pd.DataFrame({"open": g.p.first(), "high": g.p.max(), "low": g.p.min(), "close": g.p.last(),
                      "volume": g.v.sum(), "buy": g.buy.sum(), "sell": g.sell.sum()})
    return b


def contracts_in_zips(market):
    for z in sorted(glob.glob(os.path.join(ROOT, f"{market}-*.zip"))):
        try:
            with zipfile.ZipFile(z) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".scid"):
                        yield z, name
        except zipfile.BadZipFile:
            print("  damaged zip skipped:", os.path.basename(z))


def build(market):
    os.makedirs(CACHE, exist_ok=True)
    seen = set(); t0 = time.time()
    items = list(contracts_in_zips(market))
    print(f"{market}: {len(items)} contract files in {len(set(z for z, _ in items))} zip parts")
    for k, (z, name) in enumerate(items, 1):
        sym = re.sub(r"[^A-Z0-9]", "", os.path.basename(name).split("-")[0].upper())
        out = os.path.join(CACHE, f"{sym}.parquet")
        if sym in seen or os.path.exists(out):
            seen.add(sym); continue
        seen.add(sym)
        try:
            with zipfile.ZipFile(z) as zf:
                raw = zf.read(name)
            b = bars_from_scid(raw); del raw
            if b is not None and len(b):
                b.insert(0, "contract", sym); b.to_parquet(out, compression="zstd")
            print(f"  {k}/{len(items)} {sym}: {0 if b is None else len(b):,} minutes  ({(time.time() - t0) / 60:.0f} min so far)")
        except MemoryError:
            print(f"  {sym}: not enough memory - close other programs and run again")
        except Exception as e:
            print(f"  {sym}: skipped ({type(e).__name__} {str(e)[:80]})")
    # continuous series: for every trading day (17:00 CT -> 16:00 CT) use the contract with the most volume
    files = [f for f in glob.glob(os.path.join(CACHE, "*.parquet")) if os.path.basename(f).startswith(market)]
    if not files: print(f"{market}: nothing found"); return
    B = pd.concat([pd.read_parquet(f) for f in files])
    B.index.name = "t"; B = B.reset_index()
    B["day"] = (B.t + pd.Timedelta(hours=7)).dt.normalize()            # 17:00 CT belongs to the next trading day
    vol = B.groupby(["day", "contract"]).volume.sum().reset_index()
    front = vol.sort_values("volume").groupby("day").tail(1)[["day", "contract"]]
    C = B.merge(front, on=["day", "contract"]).sort_values("t").drop(columns=["day"])
    C.to_parquet(os.path.join(OUT, f"{market}_1m.parquet"), compression="zstd", index=False)
    print(f"{market}: continuous 1-minute series {C.t.min()} -> {C.t.max()}, {len(C):,} minutes, "
          f"{C.contract.nunique()} contracts used, {os.path.getsize(os.path.join(OUT, f'{market}_1m.parquet')) / 1e6:.0f} MB")


if __name__ == "__main__":
    for m in (sys.argv[1:] or ["CL", "GC"]):
        build(m)
    print("\nDONE - tell Claude it's finished.")
