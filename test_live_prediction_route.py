"""CLEAN public prediction route smoke: actual Pages and Render HTTP, no fabricated forecast."""
import os
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

PAGES = "https://ikst2512-eng.github.io/boat-edge-clean/"
RENDER = "https://boat-edge-clean.onrender.com/"

@unittest.skipUnless(os.getenv("CLEAN_LIVE_SMOKE") == "1", "opt-in network check")
class LivePredictionRouteSmoke(unittest.TestCase):
    def test_pages_has_current_prediction_fallback(self):
        with urlopen(Request(PAGES, headers={"User-Agent":"CLEAN-live-smoke"}), timeout=35) as response:
            self.assertEqual(response.status, 200)
            page=response.read(2500000).decode("utf-8")
        self.assertIn("https://boat-edge-clean.onrender.com/api/predictions?hd=", page)
        self.assertIn("async function loadPredictions(", page)

    def test_render_validation_and_cors(self):
        url=RENDER+"api/predictions?hd=invalid&jcd=01&rno=1"
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(url, headers={"Origin":"https://ikst2512-eng.github.io"}),timeout=45)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(caught.exception.headers.get("Access-Control-Allow-Origin"),"https://ikst2512-eng.github.io")

    def test_render_health(self):
        with urlopen(RENDER+"healthz",timeout=45) as response:
            self.assertEqual(response.status,200)
            self.assertEqual(response.read(),b"ok")

if __name__=="__main__":
    unittest.main()
