"""Regression tests for HEAD health probes without network side effects."""
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import server


class HeadHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    def test_head_routes_do_not_fetch_data(self):
        with patch.object(server, "get_odds", side_effect=AssertionError("odds fetch")), patch.object(
            server, "get_predictions", side_effect=AssertionError("prediction fetch")
        ):
            for path in ("/", "/index.html", "/healthz"):
                with self.subTest(path=path):
                    with urlopen(Request(self.base + path, method="HEAD"), timeout=3) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), b"")
                        self.assertEqual(response.headers["Content-Length"], "0")
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base + "/missing", method="HEAD"), timeout=3)
            self.assertEqual(caught.exception.code, 404)

    def test_get_health_still_works(self):
        with urlopen(self.base + "/healthz", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok")


if __name__ == "__main__":
    unittest.main()
