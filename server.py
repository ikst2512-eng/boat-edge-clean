from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import os

ROOT = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Share links and in-app browsers may append tracking query parameters.
        # Match the URL path, never the query string.
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path in ("/", "/index.html"):
            body = (ROOT / "index.html").read_bytes()
            status, kind = 200, "text/html; charset=utf-8"
        elif path == "/healthz":
            body = b"ok"
            status, kind = 200, "text/plain; charset=utf-8"
        elif path == "/favicon.ico":
            body = b""
            status, kind = 204, "image/x-icon"
        else:
            body = b"not found"
            status, kind = 404, "text/plain; charset=utf-8"

        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(body)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
