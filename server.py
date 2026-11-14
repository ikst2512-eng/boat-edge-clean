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

def deployed_commit():
    """Expose only a genuine Render commit SHA; never infer deployment from main."""
    value = os.environ.get("RENDER_GIT_COMMIT", "")
    return value.lower() if re.fullmatch(r"[0-9a-fA-F]{40}", value) else None

LOCK = threading.Lock()
CACHE = {}
INFLIGHT = set()
ALL_TICKETS = {"-".join(map(str, p)) for p in permutations(range(1, 7), 3)}


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
    logging.warning("odds_matrix_shape_mismatch tables=%s table_row_counts=%s table_width_histograms=%s", len(parser.tables), [len(rows) for rows in parser.tables[:12]], [{width: sum(len(row) == width for row in rows) for width in sorted({len(row) for row in rows})} for rows in parser.tables[:12]])
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
        if saved and now - saved[0] < (60 if saved[1] == 200 else 5):
            return saved[1], saved[2]
        if key in INFLIGHT:
            return 202, {"ok": False, "message": "オッズを取得中です。少ししてからもう一度押してください。"}
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
        result = 200, {"ok": True, "hd": hd, "jcd": jcd, "rno": int(rno), "odds": odds, "fetched_at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        logging.warning("odds_refresh_failed race=%s-%s-%s reason=%s: %s", hd, jcd, rno, type(exc).__name__, str(exc)[:160])
        result = 503, {"ok": False, "message": "このレースのオッズをまだ取得できません。開催状況を確認し、少ししてから更新してください。"}
    with LOCK:
        CACHE[key] = (time.monotonic(), result[0], result[1])
        INFLIGHT.discard(key)
    return result


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
    # A saved pre-result candidate is preferable to recomputing a past race.
    # It is research evidence only: never call it validated or formal Fresh.
    code = f"{hd}{int(jcd):02d}{int(rno):02d}"
    archive = ROOT / "prospective_predictions" / (code + ".json")
    if archive.is_file() and not archive.is_symlink():
        try:
            if archive.stat().st_size > 20000:
                raise ValueError("archive too large")
            record = json.loads(archive.read_text(encoding="utf-8"))
            picks = record.get("predictions")
            generated = datetime.fromisoformat(record["generated_at"])
            cutoff = datetime.fromisoformat(record["cutoff_jst"])
            if (record.get("race_code") != code or
                record.get("status") != "prospective_candidate" or
                record.get("validated") is not False or
                generated.tzinfo is None or cutoff.tzinfo is None or
                generated >= cutoff or not record.get("model_version") or
                not isinstance(picks, list) or len(picks) != 10 or
                any(not isinstance(t, str) or
                    re.fullmatch(r"[1-6]-[1-6]-[1-6]", t) is None or
                    len(set(t.split("-"))) != 3 for t in picks) or
                len(set(picks)) != 10):
                raise ValueError("unverified archive")
            # An archived candidate is research-only; source receipt order may be unverified.
            receipts = [datetime.fromisoformat(record[k]) for k in
                        ("source_title_received_jst", "source_cards_received_jst")
                        if isinstance(record.get(k), str)]
            receipt_order_verified = (
                len(receipts) == 2 and all(
                    t.tzinfo is not None and t <= generated for t in receipts)
            )
            return 200, {"ok": True, "status": "research",
                         "receipt_order_verified": receipt_order_verified,
                         "provenance_warning": None if receipt_order_verified else "SOURCE_RECEIPT_ORDER_UNVERIFIED",
                         "validated": False, "formal": False,
                         "predictions": picks, "model_version": record["model_version"],
                         "generated_at": record["generated_at"],
                         "source": "saved_prospective_candidate",
                         "message": ("締切前保存と記録された研究候補ですが、入力元の受信時刻が生成時刻より後のため時刻証拠は未検証です。正式予想ではありません。" if not receipt_order_verified else "締切前保存の研究候補です。正式検証済み予想ではありません。")}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logging.warning("archived_prospective_invalid %s", code)
            return 503, {"ok": False, "status": "error", "predictions": [],
                         "message": "保存済み研究予想の原本が検証できません。"}
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
        return 200, {"ok": True, "status": "available", "predictions": tickets, "model_version": str(record["model_version"])[:80], "generated_at": str(record["generated_at"])[:40]}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        logging.warning("prediction_feed_invalid %s", type(exc).__name__)
        return 503, {"ok": False, "status": "error", "predictions": [], "message": "予想データを検証できません。予想の掲載を停止しています。"}


def get_restored_scenario_preview(params, *, card_loader=None, now=None):
    """Read-only OLD scenario engine, never post-result, never saved/formal.

    The old scorer and current CLEAN V2 archives are deliberately independent.
    History/results/odds are not opened; a past race cannot be recomputed.
    """
    hd = params.get("hd", [""])[0]
    jcd = params.get("jcd", [""])[0]
    rno = params.get("rno", [""])[0]
    if (not re.fullmatch(r"20[0-9]{6}", hd)
            or not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd)
            or not re.fullmatch(r"[1-9]|1[0-2]", rno)):
        return 400, {"ok": False, "status": "invalid_race"}
    try:
        datetime.strptime(hd, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "status": "invalid_race"}
    if card_loader is None:
        from clean_racecard import racecard
        card_loader = racecard
    from legacy_scenario_engine import restored_scenario_preview
    try:
        card = card_loader(hd, jcd, rno)
        output = restored_scenario_preview(card, now=now)
        if (output.get("model_version") !=
                "LEGACY_SCENARIO_SCORE_RESTORED_FOUR_MODE_REFERENCE_V1"
                or output.get("formal") is not False or
                output.get("production_buy_approved") is not False):
            raise ValueError("unsafe_research_preview")
        return 200, output
    except ValueError as exc:
        reason = str(exc)
        # No retrospective generation. Return an explicit unavailable state.
        if reason in ("race_deadline_already_passed", "not_a_live_pre_result_race",
                      "race_already_closed"):
            return 422, {"ok": False, "status": "past_race_not_recomputed"}
        if reason in ("race_card_not_available", "deadline_not_available",
                      "six_racers_unavailable"):
            return 404, {"ok": False, "status": "source_not_published"}
        logging.info("scenario_preview_rejected reason=%s", reason[:100])
        return 422, {"ok": False, "status": "unverified_source", "reason": reason[:100]}
    except (OSError, TimeoutError, KeyError, TypeError, AttributeError) as exc:
        logging.warning("scenario_preview_unavailable reason=%s", type(exc).__name__)
        return 503, {"ok": False, "status": "source_temporarily_unavailable"}



def get_v133_reference_preview(params, *, card_loader=None, now=None):
    """Original V127/V133 calculation on verified live inputs, never post-result."""
    hd = params.get("hd", [""])[0]
    jcd = params.get("jcd", [""])[0]
    rno = params.get("rno", [""])[0]
    if (not re.fullmatch(r"20[0-9]{6}", hd)
            or not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd)
            or not re.fullmatch(r"[1-9]|1[0-2]", rno)):
        return 400, {"ok": False, "status": "invalid_race"}
    try:
        datetime.strptime(hd, "%Y%m%d")
    except ValueError:
        return 400, {"ok": False, "status": "invalid_race"}
    if card_loader is None:
        from clean_racecard import racecard
        card_loader = racecard
    from legacy_v133_reference_engine import v133_reference_preview
    try:
        output = v133_reference_preview(card_loader(hd, jcd, rno), now=now)
        if (output.get("race_code") != hd+jcd+str(int(rno)).zfill(2)
                or output.get("formal") is not False
                or output.get("production_buy_approved") is not False):
            raise ValueError("unsafe_v133_reference")
        return 200, output
    except ValueError as exc:
        reason = str(exc)
        if reason in ("race_deadline_already_passed", "not_a_live_pre_result_race",
                      "race_already_closed"):
            return 422, {"ok": False, "status": "past_race_not_recomputed"}
        if reason in ("race_card_not_available", "deadline_not_available",
                      "six_racers_unavailable"):
            return 404, {"ok": False, "status": "source_not_published"}
        logging.info("v133_reference_rejected reason=%s", reason[:100])
        return 422, {"ok": False, "status": "unverified_source", "reason": reason[:100]}
    except (OSError, TimeoutError, KeyError, TypeError, AttributeError) as exc:
        logging.warning("v133_reference_unavailable reason=%s", type(exc).__name__)
        return 503, {"ok": False, "status": "source_temporarily_unavailable"}


# The historical holdout evaluator reads and validates many saved races.
# Never perform that computation inside a public request handler.
_HOLDOUT_LOCK = threading.Lock()
_HOLDOUT_STATE = {"value": None, "expires": 0.0, "running": False,
                  "started": None, "last_duration": None, "last_error": None}
_HOLDOUT_TTL_SECONDS = 900
_HOLDOUT_PROCESS_BOOT = time.monotonic()
_HOLDOUT_PROCESS_ID = os.getpid()

def _compute_holdout_status():
    from compare_topn_signal70_days import report
    dates = sorted({p.stem[:8] for p in (ROOT / "prospective_predictions").glob("20??????????.json")})
    # This endpoint reports *later* holdouts only; auditing discovery and
    # earlier exploratory races cannot affect its response.
    holdout_dates = [day for day in dates if day > "20261029"]
    first_add_probes = {}
    if holdout_dates:
        from audit_clean_first_add import bulk_first_add, inspect
        with bulk_first_add(ROOT):
            # Compare the exact production Git audit against frozen examples
            # independently verified using full Git history on CI.
            for code in ("202610301306", "202610312412",
                         "202611011306", "202611022412"):
                try:
                    proof = inspect("prospective_predictions/" + code + ".json", ROOT)
                    first_add_probes[code] = {"ok": True,
                        "sha": proof["first_add_sha"],
                        "first_committer_at": proof["first_committer_at"]}
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    late = str(exc) == "first Git commit not before prospective cutoff"
                    first_add_probes[code] = {"ok": False,
                        "reason": type(exc).__name__,
                        "cutoff_rejected": late,
                        "reason_detail": str(exc)[:160]}
                    if late:
                        # Diagnostic only: preserve inspect() rejection while
                        # identifying the *actual* first-add commit used by Render.
                        try:
                            from audit_clean_first_add import first_add
                            import json as _json
                            raw, sha, when = first_add(
                                "prospective_predictions/" + code + ".json", ROOT)
                            cutoff = datetime.fromisoformat(_json.loads(raw)["cutoff_jst"])
                            first_add_probes[code].update(
                                sha=sha, first_committer_at=when.isoformat(),
                                minutes_before_cutoff=round(
                                    (cutoff - when).total_seconds()/60, 2))
                        except (ValueError, KeyError, TypeError, OSError):
                            first_add_probes[code]["commit_details_unavailable"] = True
            data = report(holdout_dates)
    else:
        data = {"later_holdout_days": 0, "later_holdout_evaluated_races": 0}
    # Keep rejected audits separate from races with unavailable confirmed results.
    # Neither may enter a Top-N hit-rate denominator.
    days = data.get("days", [])
    awaiting = sum(g["awaiting_result"] for d in days for g in d["groups"].values())
    rejected = sum(g["rejected"] for d in days for g in d["groups"].values())
    archived = sum(d["archived"] for d in days)
    rejection_reasons = {}
    for day in days:
        for group in day["groups"].values():
            for reason, count in group.get("rejection_reasons", {}).items():
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + count
    return {"schema": "CLEAN_SIGNAL70_HOLDOUT_STATUS_V1",
            "later_holdout_days": data["later_holdout_days"],
            "evaluated_holdout_races": data["later_holdout_evaluated_races"],
            "awaiting_result_races": awaiting,
            "audit_rejected_races": rejected,
            "audit_rejection_reasons": rejection_reasons,
            "archived_candidates": archived,
            "first_add_probes": first_add_probes,
            "discovery_day": "20261029", "independently_validated": False}

def _prepare_holdout_history():
    """Hydrate Render's shallow checkout without changing HEAD or any files.

    Runs only in the existing background worker. The audit still independently
    rejects incomplete history and changed original blobs after this fetch.
    """
    if os.environ.get("RENDER") != "true":
        return
    import subprocess
    shallow = subprocess.check_output(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=ROOT, text=True, timeout=10).strip()
    if shallow == "false":
        return
    if shallow != "true":
        raise ValueError("indeterminate local git history")
    subprocess.run(
        ["git", "fetch", "--unshallow", "--no-tags",
         "https://github.com/ikst2512-eng/boat-edge-clean.git", "main"],
        cwd=ROOT, check=True, timeout=90, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})

def _refresh_holdout_status():
    with _HOLDOUT_LOCK:
        started = _HOLDOUT_STATE["started"] or time.monotonic()
    error = None
    try:
        _prepare_holdout_history()
        result = _compute_holdout_status()
    except Exception as exc:
        logging.exception("holdout_status_unavailable")
        error = type(exc).__name__
        result = None
    elapsed = time.monotonic() - started
    with _HOLDOUT_LOCK:
        _HOLDOUT_STATE["value"] = result
        _HOLDOUT_STATE["expires"] = time.monotonic() + _HOLDOUT_TTL_SECONDS
        _HOLDOUT_STATE["running"] = False
        _HOLDOUT_STATE["last_duration"] = round(elapsed, 2)
        _HOLDOUT_STATE["last_error"] = error
    logging.info("holdout_refresh_finished duration_seconds=%.2f outcome=%s",
                 elapsed, "ready" if result is not None else error)

def holdout_status():
    now = time.monotonic()
    with _HOLDOUT_LOCK:
        if now >= _HOLDOUT_STATE["expires"] and not _HOLDOUT_STATE["running"]:
            _HOLDOUT_STATE["running"] = True
            _HOLDOUT_STATE["started"] = now
            _HOLDOUT_STATE["last_error"] = None
            threading.Thread(target=_refresh_holdout_status, daemon=True, name="holdout-refresh").start()
        value = _HOLDOUT_STATE["value"]
        fresh = value is not None and now < _HOLDOUT_STATE["expires"]
        running = _HOLDOUT_STATE["running"]
        started = _HOLDOUT_STATE["started"]
        last_duration = _HOLDOUT_STATE["last_duration"]
        last_error = _HOLDOUT_STATE["last_error"]
    if fresh:
        return 200, value
    # Report operational status only. Never fabricate research evidence.
    return 503, {"ok": False,
                 "error": "HOLDOUT_PENDING" if running else "HOLDOUT_UNAVAILABLE",
                 "retryable": True,
                 "running": running,
                 "elapsed_seconds": round(max(0, now - started), 1) if running and started is not None else None,
                 "last_duration_seconds": last_duration,
                 "last_error_type": last_error,
                 "worker_pid": _HOLDOUT_PROCESS_ID,
                 "process_uptime_seconds": round(time.monotonic() - _HOLDOUT_PROCESS_BOOT, 1)}

class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        # Health checks must not trigger predictions or upstream fetches.
        path = urlsplit(self.path).path.rstrip('/') or '/'
        if path in ('/', '/index.html', '/forecast', '/exhibition', '/card', '/results', '/review', '/selection', '/daily-findings', '/healthz'):
            status = 200
        else:
            status = 404
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', '0')
        self.send_header('Cache-Control', 'no-store')
        if path == '/healthz':
            revision = deployed_commit()
            if revision:
                self.send_header("X-Boat-Edge-Deploy-Commit", revision)
        self.end_headers()

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path in ("/", "/index.html", "/forecast", "/exhibition", "/card", "/results", "/review"):
            body = (ROOT / "index.html").read_bytes()
            status, kind = 200, "text/html; charset=utf-8"
        elif path == "/styles.css":
            body = (ROOT / "styles.css").read_bytes()
            status, kind = 200, "text/css; charset=utf-8"
        elif path == "/navigation.js":
            body = (ROOT / "navigation.js").read_bytes()
            status, kind = 200, "application/javascript; charset=utf-8"
        elif path == "/candidate_history.js":
            body = (ROOT / "candidate_history.js").read_bytes()
            status, kind = 200, "application/javascript; charset=utf-8"
        elif path == "/entry_scenario.js":
            body = (ROOT / "entry_scenario.js").read_bytes()
            status, kind = 200, "application/javascript; charset=utf-8"
        elif path == "/secondary_navigation.js":
            body = (ROOT / "navigation.js").read_bytes()
            status, kind = 200, "application/javascript; charset=utf-8"
        elif path == "/daily-findings":
            body = (ROOT / "daily_findings.html").read_bytes().replace(b"</body>", b'<script src="/navigation.js" defer></script></body>')
            status, kind = 200, "text/html; charset=utf-8"
        elif path == "/api/daily-findings":
            try:
                from daily_findings import daily_findings
                status, data = 200, daily_findings()
            except (ValueError, KeyError, OSError, TypeError):
                logging.exception("daily_findings_unavailable")
                status, data = 503, {"ok": False, "error": "FINDINGS_UNAVAILABLE"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/selection":
            body = (ROOT / "selection.html").read_bytes().replace(b"</body>", b'<script src="/navigation.js" defer></script></body>')
            status, kind = 200, "text/html; charset=utf-8"
        elif path == "/api/signal70-holdout-status":
            status, response = holdout_status()
            body=json.dumps(response,ensure_ascii=False).encode("utf-8")
            kind="application/json; charset=utf-8"
        elif path == "/api/candidate-history":
            from candidate_history import daily_candidate_history
            params = parse_qs(parsed.query)
            status, data = daily_candidate_history(params.get("date", [""])[0])
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/four-mode-archive":
            from four_mode_archive_api import archived_four_modes
            params = parse_qs(parsed.query)
            status, data = archived_four_modes(params.get("code", [""])[0])
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/prospective-topn":
            from evaluate_clean_prospective_cohort import cohort
            params = parse_qs(parsed.query)
            day = params.get("day", [""])[0]
            try:
                data = cohort(day)
                status = 200
            except (ValueError, KeyError, OSError, TypeError) as exc:
                logging.exception("prospective_topn_unavailable")
                status, data = 422 if str(exc) == "invalid day" else 503, {"ok": False, "error": "TOPN_UNAVAILABLE"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/selection-research":
            try:
                from selection_dual import report
                data = report()
                status = 200
            except (ValueError, KeyError, OSError, TypeError):
                logging.exception("selection_research_unavailable")
                status, data = 503, {"ok": False, "error": "RESEARCH_DATA_UNAVAILABLE"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/healthz":
            body = b"ok"
            status, kind = 200, "text/plain; charset=utf-8"
        elif path == "/api/clean-schedule":
            from clean_schedule import clean_schedule
            params = parse_qs(parsed.query)
            status, data = clean_schedule(params.get("date", [""])[0])
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/clean-result":
            from clean_results import read_result
            params = parse_qs(parsed.query)
            status, data = read_result(
                params.get("hd", [""])[0],
                params.get("jcd", [""])[0],
                params.get("rno", [""])[0],
            )
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/odds":
            status, data = get_odds(parse_qs(parsed.query))
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/research-snapshot":
            from independent_feed import research_snapshot
            params = parse_qs(parsed.query)
            status, data = research_snapshot(
                params.get("hd", [""])[0],
                params.get("jcd", [""])[0],
                params.get("rno", [""])[0],
            )
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/clean-racecard":
            from clean_racecard import racecard
            params = parse_qs(parsed.query)
            try:
                data = racecard(params.get("hd", [""])[0], params.get("jcd", [""])[0], params.get("rno", [""])[0])
                status = 200
            except (ValueError, OSError, TimeoutError, KeyError, TypeError) as exc:
                reason = str(exc)
                if isinstance(exc, ValueError) and reason in ("invalid_race_key", "race_already_closed"):
                    status = 422
                elif isinstance(exc, ValueError) and reason in ("race_card_not_available", "deadline_not_available", "six_racers_unavailable"):
                    status = 404
                else:
                    status = 503
                if status == 404:
                    logging.info("clean_racecard_not_found hd=%s jcd=%s rno=%s reason=%s",
                                 params.get("hd", [""])[0], params.get("jcd", [""])[0],
                                 params.get("rno", [""])[0], reason[:100])
                data = {"ok": False, "status": "unavailable", "reason": reason[:100]}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/v133-reference-preview":
            status, data = get_v133_reference_preview(parse_qs(parsed.query))
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            kind = "application/json; charset=utf-8"
        elif path == "/api/legacy-scenario-preview":
            status, data = get_restored_scenario_preview(parse_qs(parsed.query))
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
        if path == "/healthz":
            revision = deployed_commit()
            if revision:
                self.send_header("X-Boat-Edge-Deploy-Commit", revision)
        if path in ("/api/clean-schedule", "/api/predictions", "/api/clean-result", "/api/clean-racecard", "/api/prospective-topn", "/api/odds", "/api/four-mode-archive", "/api/candidate-history", "/api/legacy-scenario-preview", "/api/v133-reference-preview"):
            # Read-only CLEAN data is consumed by the GitHub Pages origin.
            self.send_header("Access-Control-Allow-Origin", "https://ikst2512-eng.github.io")
        self.end_headers()
        if body:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # The client may disconnect during rapid race navigation.
                # Response handling has already finished; avoid a noisy traceback.
                return

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
