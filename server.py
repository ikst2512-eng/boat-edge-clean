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
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()
CACHE = {}
INFLIGHT = set()
ALL_TICKETS = {"-".join(map(str, p)) for p in permutations(range(1, 7), 3)}
TICKET_RE = re.compile(r"(?<![0-9])([1-6])\s*[-－]\s*([1-6])\s*[-－]\s*([1-6])\s*(?:[：:]|\s)+\s*([0-9]+(?:\.[0-9]+)?)(?![0-9])")


from html.parser import HTMLParser

class OddsTableReader(HTMLParser):
    """Extract table cells in visual row order, preserving rowspan semantics in odds table."""
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.depth += 1
            if self.depth == 1:
                self.table = []
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif self.depth > 1 and tag in ("td", "th") and self.cell is not None:
            pass

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.depth == 1 and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.depth == 1 and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.table)
                self.table = None

def parse_official_odds_table(html):
    """Six first-place columns, 20 second/third combinations per column; fail closed."""
    parser = OddsTableReader()
    parser.feed(html)
    for rows in parser.tables:
        # Official odds matrix: 20 rows, six repeating groups. Header rows may surround it.
        for begin in range(max(0, len(rows) - 19)):
            block = rows[begin:begin + 20]
            if len(block) != 20:
                continue
            odds = {}
            try:
                for idx, row in enumerate(block):
                    needed = 18 if idx % 4 == 0 else 12
                    if len(row) != needed:
                        raise ValueError("Unexpected odds row width")
                    group_size = 3 if idx % 4 == 0 else 2
                    for first in range(1, 7):
                        group = row[(first-1)*group_size:first*group_size]
                        if group_size == 3:
                            second, third, value = group
                        else:
                            third, value = group
                            second = block[idx-(idx%4)][(first-1)*3]
                        a, b, c = first, int(second), int(third)
                        if len({a,b,c}) != 3:
                            raise ValueError("Invalid combination")
                        odd = float(value.replace(",", ""))
                        if not (1 <= odd <= 1000000):
                            raise ValueError("Invalid odds")
                        key = f"{a}-{b}-{c}"
                        if key in odds:
                            raise ValueError("Duplicate combination")
                        odds[key] = odd
                if set(odds) == ALL_TICKETS:
                    return odds
            except (ValueError, IndexError, TypeError):
                continue
    raise ValueError("Official odds table could not be parsed as 120 unique combinations")

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
        if key in INFLIGHT:
            return 202, {"ok": False, "message": "オッズを取得中です。少ししてからもう一度押してください。"}
        if saved and now - saved[0] < (60 if saved[1] == 200 else 5):
            return saved[1], saved[2]
        INFLIGHT.add(key)
    logging.info("odds_refresh_started venue=%s race=%s", jcd, rno)
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
        odds = parse_official_odds_table(html)
        result = 200, {"ok": True, "odds": odds, "fetched_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        logging.warning("odds_refresh_failed race=%s-%s-%s reason=%s: %s", hd, jcd, rno, type(exc).__name__, str(exc)[:160])
        result = 503, {"ok": False, "message": "このレースのオッズをまだ取得できません。開催状況を確認し、少ししてから更新してください。"}
    with LOCK:
        CACHE[key] = (time.monotonic(), result[0], result[1])
        INFLIGHT.discard(key)
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
