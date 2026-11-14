"""Isolated live-handler CORS contract for the read-only four-mode archive.

Unlike a string-only guard, this starts a real local HTTP server and inspects
response headers for success and error statuses. It never hits Render or
changes archived predictions.
"""
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

from server import Handler


PAGES_ORIGIN = "https://ikst2512-eng.github.io"
UNTRUSTED_ORIGIN = "https://untrusted-site.example"


class FourModeArchiveCorsHotfixTest(unittest.TestCase):
    def test_archive_header_is_limited_to_pages_on_all_response_statuses(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as httpd:
            thread = Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                for status in (200, 404, 422):
                    for origin in (PAGES_ORIGIN, UNTRUSTED_ORIGIN):
                        with self.subTest(status=status, origin=origin):
                            with patch(
                                "four_mode_archive_api.archived_four_modes",
                                return_value=(status, {"ok": status == 200}),
                            ):
                                connection = HTTPConnection(
                                    "127.0.0.1", httpd.server_port, timeout=5
                                )
                                try:
                                    connection.request(
                                        "GET", "/api/four-mode-archive?code=202611061006",
                                        headers={"Origin": origin},
                                    )
                                    response = connection.getresponse()
                                    response.read()
                                    self.assertEqual(response.status, status)
                                    self.assertEqual(
                                        response.getheader("Access-Control-Allow-Origin"),
                                        PAGES_ORIGIN,
                                    )
                                    self.assertNotEqual(
                                        response.getheader("Access-Control-Allow-Origin"),
                                        UNTRUSTED_ORIGIN,
                                    )
                                finally:
                                    connection.close()

                # No new cross-origin permission on a health endpoint.
                connection = HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                try:
                    connection.request("GET", "/healthz", headers={"Origin": PAGES_ORIGIN})
                    response = connection.getresponse()
                    self.assertEqual(response.read(), b"ok")
                    self.assertEqual(response.status, 200)
                    self.assertIsNone(
                        response.getheader("Access-Control-Allow-Origin")
                    )
                finally:
                    connection.close()
            finally:
                httpd.shutdown()
                thread.join(timeout=5)


    def test_healthz_reports_runtime_revision_without_changing_body_or_cors(self):
        # A main-branch commit is not the currently deployed Render revision.
        # Only Render's runtime env may provide the health response SHA.
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as httpd:
            thread = Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                for sha, expected in [
                    ("a" * 40, "a" * 40),
                    ("B" * 40, "b" * 40),
                    ("not-a-commit", None),
                    ("", None),
                ]:
                    for method in ("GET", "HEAD"):
                        with self.subTest(commit=sha, method=method):
                            with patch.dict("os.environ", {"RENDER_GIT_COMMIT": sha}):
                                connection = HTTPConnection(
                                    "127.0.0.1", httpd.server_port, timeout=5
                                )
                                try:
                                    connection.request(
                                        method, "/healthz",
                                        headers={"Origin": PAGES_ORIGIN},
                                    )
                                    response = connection.getresponse()
                                    body = response.read()
                                    self.assertEqual(response.status, 200)
                                    self.assertEqual(body, b"ok" if method == "GET" else b"")
                                    self.assertEqual(
                                        response.getheader("X-Boat-Edge-Deploy-Commit"),
                                        expected,
                                    )
                                    self.assertIsNone(
                                        response.getheader("Access-Control-Allow-Origin")
                                    )
                                finally:
                                    connection.close()
            finally:
                httpd.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
