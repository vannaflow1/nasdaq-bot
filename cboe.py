"""cboe.py - one place that downloads CBOE's free delayed option chains for every Volta job.

Why (plain words): since Friday 20 Nov 2026 CBOE refuses (HTTP 403) every request that comes from GitHub's servers.
Options data is used by the evening recap, tomorrow's range forecast (which the F10/F13 forward tests need), the
option-chain archive, the options nerd and the SPX summary. So every download now goes:

    1. straight to CBOE (as before; fastest when it works),
    2. if that is refused or fails: through Volta's own Cloudflare Worker (route /cboe), which asks CBOE from
       Cloudflare's servers and passes the answer back unchanged.

The worker needs the same private key as the /ai route; it is derived from the CLOUDFLARE_API_TOKEN secret, so a job
that wants the fallback needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in its env. Without them only step 1 runs.
Only option-chain symbols are relayed (the worker refuses anything else).

Use:  raw = cboe.chain("QQQ")      # parsed JSON, same as before
      body = cboe.download("_NDX") # raw bytes, already un-gzipped
Self-check: python cboe.py QQQ   (prints where the data came from and its size)"""
import gzip, hashlib, json, os, re, sys, time, urllib.error, urllib.request

BASE = "https://cdn-api.cboe.com/api/global/delayed_quotes/options/{}.json"
UA = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
LAST = {"via": None}                                   # "direct" | "worker" - for logs
_URL = {}


def code_from(url_or_code):
    m = re.search(r"/options/([A-Z_]{1,8})\.json", url_or_code)
    return m.group(1) if m else url_or_code


def _unzip(body):
    return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body


def _worker():
    """(url, key) of Volta's worker /cboe route, or None when the Cloudflare secrets are not in this job's env."""
    tok, acc = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(), os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not tok or not acc: return None
    if "u" not in _URL:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/subdomain",
            headers={"Authorization": f"Bearer {tok}"}), timeout=30).read())
        _URL["u"] = f"https://minivanna.{r['result']['subdomain']}.workers.dev/cboe"
    return _URL["u"], hashlib.sha256(f"{tok}-volta-learn".encode()).hexdigest()


def download(url_or_code, timeout=180):
    code = code_from(url_or_code)
    try:
        body = urllib.request.urlopen(urllib.request.Request(BASE.format(code), headers=UA), timeout=timeout).read()
        LAST["via"] = "direct"; return _unzip(body)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        first = e
    w = _worker()
    if not w: raise first
    url, key = w
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps({"code": code}).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Learn-Key": key,
                                                  "User-Agent": "volta-cboe", "Accept-Encoding": "gzip"})
            body = urllib.request.urlopen(req, timeout=timeout).read()
            LAST["via"] = "worker"; return _unzip(body)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 2:
                raise RuntimeError(f"CBOE {code}: direct failed ({first}); via worker failed ({e})") from e
            time.sleep([15, 45][attempt])


def chain(url_or_code, timeout=180):
    raw = json.loads(download(url_or_code, timeout))
    if not isinstance(raw, dict) or "data" not in raw: raise ValueError(f"CBOE {code_from(url_or_code)}: unexpected answer")
    return raw


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    b = download(c); print(f"{c}: {len(b) / 1e6:.1f} MB via {LAST['via']}")
