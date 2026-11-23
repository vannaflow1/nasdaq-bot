import json, os, unittest, urllib.error
from unittest import mock
from _util import ROOT
import cboe


class Resp:
    def __init__(self, body): self.body = body
    def read(self): return self.body


class Fallback(unittest.TestCase):
    def setUp(self): cboe._URL.clear()

    def test_direct_when_cboe_answers(self):
        with mock.patch("urllib.request.urlopen", lambda req, timeout: Resp(b'{"data":{"options":[]}}')):
            self.assertEqual(cboe.chain("QQQ"), {"data": {"options": []}}); self.assertEqual(cboe.LAST["via"], "direct")

    def test_refused_goes_through_the_worker_with_the_key(self):
        seen = []
        def fake(req, timeout):
            u = req.full_url; seen.append(u)
            if "cboe.com" in u: raise urllib.error.HTTPError(u, 403, "Forbidden", {}, None)
            if "subdomain" in u: return Resp(b'{"result":{"subdomain":"x"}}')
            self.assertEqual(json.loads(req.data), {"code": "_NDX"}); self.assertEqual(len(req.get_header("X-learn-key")), 64)
            return Resp(b'{"data":{"options":[1]}}')
        env = {"CLOUDFLARE_API_TOKEN": "t", "CLOUDFLARE_ACCOUNT_ID": "a"}
        with mock.patch.dict(os.environ, env), mock.patch("urllib.request.urlopen", fake):
            self.assertEqual(cboe.chain("https://cdn-api.cboe.com/api/global/delayed_quotes/options/_NDX.json")["data"]["options"], [1])
        self.assertEqual(cboe.LAST["via"], "worker"); self.assertTrue(seen[-1].endswith("/cboe"))

    def test_no_secrets_means_the_original_error(self):
        def refuse(req, timeout): raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
        with mock.patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": ""}), mock.patch("urllib.request.urlopen", refuse):
            with self.assertRaises(urllib.error.HTTPError): cboe.download("QQQ")

    def test_gzip_is_unpacked(self):
        import gzip
        with mock.patch("urllib.request.urlopen", lambda req, timeout: Resp(gzip.compress(b'{"data":{}}'))):
            self.assertEqual(cboe.chain("SPY"), {"data": {}})


if __name__ == "__main__":
    unittest.main()
