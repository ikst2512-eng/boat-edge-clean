from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path
import json
import os
import re
import threading
import time

ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()
CACHE = {}
ALL_TICKETS = {"-".join(map(str, p)) for p in permutations(range(1, 7), 3)}
TICKET_RE = re.compile(r"(?<![0-9])([1-6])\s*[-－]\s*([1-6])\s*[-－]\s*([1-6])\s*(?:[：:]|\s)+\s*([0-9]+(?:\.[0-9]+)?)(?![0-9])")

def get_odds(params):
    hd = params.get("hd", [""])[0]
    jcd = params.get("jcd", [""])[0]
    rno = params.get("rno", [""])[0]
    if not (re.fullmatch(r"20[0-9]{6}", hd) and re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd) and re.fullmatch(r"[1-9]|1[0-2]", rno)):
        return 400, {"ok": False, "message": "日付・開催場・レース番号が不正です。"}
    try:
        datetime.strptime(hd, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "message": "開催日が不正です。"}
    key = (hd, jcd, rno)
    now = time.monotonic()
    with LOCK:
        saved = CACHE.get(key)
        if saved and now - saved[0] < 60:
            return saved[1], saved[2]
        # Reserve a short cooldown even when parsing fails; no repeated upstream flooding.
        CACHE[key] = (now, 503, {"ok": False, "message": "オッズを確認中です。少ししてから更新してください。"})
    url = "https://www.boatrace.jp/owpc/pc/race/odds3t?hd=" + hd + "&jcd=" + jcd + "&rno=" + rno
    try:
        req = Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN/1.0", "Accept": "text/html"})
        with urlopen(req, timeout=12) as response:
            if response.status != 200 or "html" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Upstream not HTML")
            raw = response.read(1500001)
            if len(raw) > 1500000:
                raise ValueError("HTML too large")
        html = raw.decode("utf-8", errors="replace")
        matches = TICKET_RE.findall(html)
        odds = {}
        for a,b,c,v in matches:
            ticket = a+"-"+b+"-"+c
            if len({a,b,c}) != 3 or ticket in odds:
                raise ValueError("Duplicate or invalid ticket")
            value = float(v)
            if not (1 <= value <= 1000000):
                raise ValueError("Invalid odds")
            odds[ticket] = value
        if set(odds) != ALL_TICKETS:
            raise ValueError("Unsupported HTML odds structure")
        result = 200, {"ok": True, "odds": odds, "fetched_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        result = 503, {"ok": False, "message": "現在このレースのオッズを取得・解析できません。時間をおいて更新してください。"}
    with LOCK:
        CACHE[key] = (time.monotonic(), result[0], result[1])
    return result

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path in ("/", "/index.html"):
            body = (ROOT / "index.html").read_bytes()
            status, kind = 200, "text/html; charset=utf-8"
        elif path == "/healthz":
            body = b"ok"
            status, kind = 200, "text/plain; charset=utf-8"
        elif path == "/api/odds":
            status, data = get_odds(parse_qs(parsed.query))
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
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
