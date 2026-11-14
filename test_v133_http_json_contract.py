"""Regression: V133 HTTP Handler must return valid JSON for both success and errors.

No official source, external network, model execution or stored forecast is read.
"""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import Handler


class V133HttpResponseContractTests(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.worker.join, timeout=3)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/api/v133-reference-preview?hd=20261114&jcd=09&rno=10"

    def test_success_is_200_json_with_pages_cors_and_real_body(self):
        expected = {"ok": True, "race_code": "202611140910", "formal": False,
                    "modes": {"narrow": {"tickets": [{"combo": "1-3-4", "p": 10.0}]}}}
        with patch("server.get_v133_reference_preview", return_value=(200, expected)) as engine:
            req = Request(self.url, headers={"Origin": "https://ikst2512-eng.github.io"})
            with urlopen(req, timeout=5) as response:
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "application/json")
                self.assertEqual(response.headers.get("Access-Control-Allow-Origin"),
                                 "https://ikst2512-eng.github.io")
                self.assertEqual(int(response.headers["Content-Length"]), len(body))
                self.assertEqual(json.loads(body), expected)
            engine.assert_called_once()

    def test_invalid_source_is_422_json_not_broken_http_stream(self):
        expected = {"ok": False, "status": "unverified_source",
                    "reason": "verified_six_exhibition_required"}
        with patch("server.get_v133_reference_preview", return_value=(422, expected)):
            req = Request(self.url, headers={"Origin": "https://ikst2512-eng.github.io"})
            with self.assertRaises(HTTPError) as caught:
                urlopen(req, timeout=5)
            response = caught.exception
            self.assertEqual(response.code, 422)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"),
                             "https://ikst2512-eng.github.io")
            self.assertEqual(json.loads(response.read()), expected)


if __name__ == "__main__":
    unittest.main()
