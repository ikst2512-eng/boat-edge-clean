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
    logging.warning("odds_matrix_shape_mismatch tables=%s sample_row_widths=%s", len(parser.tables), [list(map(len, rows[:6])) for rows in parser.tables[:3]])
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


def verify_commit_proof(proof, record, race_code):
    """Verify immutable forecast bytes against an allowlisted GitHub commit.

    Fail closed on network errors. Only the repository's trusted freeze path
    can supply proof; the source file must contain the exact record.
    """
    import hashlib
    from urllib.error import HTTPError, URLError
    sha = proof["commit_sha"]
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("invalid commit SHA")
    if record.get("race_code") != race_code:
        raise ValueError("frozen race code differs from requested race")
    path = proof.get("path", "")
    if not isinstance(race_code, str) or not re.fullmatch(r"[0-9]{12}", race_code):
        raise ValueError("invalid race code")
    if path != "fresh_snapshots/" + race_code + ".json":
        raise ValueError("untrusted proof path")
    expected = proof.get("sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("invalid frozen content hash")
    host = "https://api.github.com/repos/ikst2512-eng/boat-edge-clean"
    req = Request(host + "/commits/" + sha, headers={"User-Agent": "BOAT-EDGE-FRESH/1.0", "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=5) as response:
        metadata = json.load(response)
    actual_commit_time = datetime.fromisoformat(metadata["commit"]["committer"]["date"].replace("Z", "+00:00"))
    deadline = datetime.fromisoformat(proof["deadline_at"])
    if record.get("deadline_at") != proof["deadline_at"]:
        raise ValueError("source deadline differs from supplied deadline")
    generated = datetime.fromisoformat(record["generated_at"])
    stated_committed = datetime.fromisoformat(proof["committed_at"])
    if any(dt.tzinfo is None or dt.utcoffset() is None for dt in (deadline, generated, actual_commit_time, stated_committed)):
        raise ValueError("timezone required")
    if stated_committed != actual_commit_time:
        raise ValueError("stated commit time mismatch")
    if generated > actual_commit_time or actual_commit_time >= deadline:
        raise ValueError("commit is not before deadline")
    # A Git committer date is self-declared. Require GitHub's server-issued
    # workflow creation time as an independent pre-deadline existence witness.
    run_id = proof.get("run_id")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("missing independent GitHub run ID")
    run_req = Request(host + "/actions/runs/" + str(run_id),
                      headers={"User-Agent": "BOAT-EDGE-FRESH/1.0", "Accept": "application/vnd.github+json"})
    with urlopen(run_req, timeout=5) as response:
        run = json.load(response)
    if (run.get("head_sha") != sha or run.get("event") != "push" or
            run.get("conclusion") != "success" or run.get("head_branch") != "main" or
            run.get("path") != ".github/workflows/fresh-snapshot-witness.yml"):
        raise ValueError("run does not independently witness committed forecast")
    created_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    if created_at.tzinfo is None or created_at >= deadline or created_at < generated:
        raise ValueError("GitHub run did not start after forecast and before deadline")
    req = Request("https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/" + sha + "/" + path,
                  headers={"User-Agent": "BOAT-EDGE-FRESH/1.0"})
    with urlopen(req, timeout=5) as response:
        raw = response.read(100_001)
    if len(raw) > 100_000 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("frozen content mismatch")
    frozen = json.loads(raw)
    if frozen != {k: v for k, v in record.items() if k != "freeze_proof"}:
        raise ValueError("published frozen record differs from served record")


def get_predictions(params):
    hd = params.get("hd", [""])[0]
    jcd = params.get("jcd", [""])[0]
    rno = params.get("rno", [""])[0]
    if not (re.fullmatch(r"20[0-9]{6}", hd) and re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd) and re.fullmatch(r"[1-9]|1[0-2]", rno)):
        return 400, {"ok": False, "message": "日付・場・レース番号が不正です。"}
    try:
        datetime.strptime(hd, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "message": "日付が不正です。"}
    source = ROOT / "predictions.json"
    if not source.exists():
        # Research-only fallback; never mislabel exploratory scores as validated.
        try:
            from research_model import predict
            return 200, predict(hd, jcd, rno)
        except (ValueError, OSError, TimeoutError, KeyError, TypeError) as exc:
            logging.info("research_prediction_unavailable %s", type(exc).__name__)
            return 200, {"ok": True, "status": "unavailable", "predictions": [], "message": "研究予想の入力データが揃っていません。"}

    try:
        if source.stat().st_size > 3000000:
            raise ValueError("prediction feed too large")
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("bad feed")
        key = hd + "-" + jcd + "-" + rno
        record = payload.get(key)
        if not isinstance(record, dict):
            return 200, {"ok": True, "status": "unavailable", "predictions": [], "message": "選択したレースの予想データはありません。"}
        raw = record.get("predictions")
        if not isinstance(raw, list) or len(raw) < 10:
            raise ValueError("fewer than 10 predictions")
        tickets = []
        for item in raw[:10]:
            ticket = item.get("ticket") if isinstance(item, dict) else None
            if not isinstance(ticket, str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", ticket):
                raise ValueError("invalid ticket")
            if len(set(ticket.split("-"))) != 3 or ticket in tickets:
                raise ValueError("duplicate ticket")
            tickets.append(ticket)
        if record.get("validated") is not True or not record.get("model_version") or not record.get("generated_at"):
            raise ValueError("feed missing validation metadata")
        # Fail closed: an arbitrary validated=true flag is not evidence of a
        # pre-deadline immutable forecast. Require external commit provenance.
        proof = record.get("freeze_proof")
        if not isinstance(proof, dict):
            raise ValueError("missing frozen prediction provenance")
        commit_sha = proof.get("commit_sha")
        if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise ValueError("invalid freeze commit sha")
        try:
            deadline = datetime.fromisoformat(proof["deadline_at"])
            committed = datetime.fromisoformat(proof["committed_at"])
            generated = datetime.fromisoformat(record["generated_at"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("invalid provenance timestamps")
        if any(dt.tzinfo is None or dt.utcoffset() is None for dt in (deadline, committed, generated)):
            raise ValueError("provenance timestamps must be timezone aware")
        if not (generated <= committed < deadline):
            raise ValueError("prediction is not demonstrably committed before deadline")
        verify_commit_proof(proof, record, hd + jcd + f"{int(rno):02d}")
        return 200, {"ok": True, "status": "available", "predictions": tickets, "model_version": str(record["model_version"])[:80], "generated_at": str(record["generated_at"])[:40]}
    except (OSError, ValueError, TypeError, AttributeError, KeyError, json.JSONDecodeError) as exc:
        logging.warning("prediction_feed_invalid %s", type(exc).__name__)
        return 503, {"ok": False, "status": "error", "predictions": [], "message": "予想データを検証できません。予想の掲載を停止しています。"}

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
        elif path == "/api/predictions":
            status, data = get_predictions(parse_qs(parsed.query))
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
