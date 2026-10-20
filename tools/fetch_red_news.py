"""Download the owner's red-folder (high-impact) economic events file from his shared Google Drive link."""
import io, os, re, urllib.request, http.cookiejar
FID = "1x6KH1JlcbSSnxtd_n8SYRhCnjAd1ic8d"
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent", "Mozilla/5.0")]
d = op.open(f"https://drive.google.com/uc?export=download&id={FID}", timeout=120).read()
if d[:15].lower().startswith(b"<!doctype html") or b"<html" in d[:300].lower():
    m = re.search(rb'name="uuid" value="([^"]+)"', d); conf = re.search(rb'confirm=([0-9A-Za-z_-]+)', d)
    url = f"https://drive.usercontent.google.com/download?id={FID}&export=download&confirm=t" + (f"&uuid={m.group(1).decode()}" if m else "")
    d = op.open(url, timeout=300).read()
os.makedirs("knowledge/data", exist_ok=True)
open("knowledge/data/econ_events_red.csv", "wb").write(d)
txt = d[:2000].decode("utf-8", "ignore")
open("knowledge/research_out/fetch_red_news.txt", "w").write(f"{len(d):,} bytes\n" + txt)
print(len(d)); print(txt[:1500])
