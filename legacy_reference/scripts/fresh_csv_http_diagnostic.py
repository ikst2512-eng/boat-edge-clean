#!/usr/bin/env python3
"""Read-only PRE_RESULT CSV availability evidence; never reads race results."""
import csv
import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
day = now.strftime("%Y/%m/%d")
base = "https://boatracecsv.github.io"
sources = {
    "race_cards": f"{base}/data/programs/race_cards/{day}.csv",
    **{role: f"{base}/data/previews/{role}/{day}.csv"
       for role in ("stt", "tkz", "sui", "original_exhibition")},
}
report = {
    "schema": "BOAT_EDGE_FRESH_CSV_HTTP_DIAGNOSTIC_V1",
    "observed_at_jst": now.isoformat(timespec="seconds"),
    "target_date_jst": now.strftime("%Y-%m-%d"),
    "github_run_id": os.getenv("GITHUB_RUN_ID"),
    "github_sha": os.getenv("GITHUB_SHA"),
    "scope": "HTTP_AND_CSV_ONLY_NOT_FORMAL_FRESH_PROOF",
    "results_accessed": False,
    "formal_unlock_authorized": False,
    "sources": {},
}
for role, url in sources.items():
    entry = {"url": url, "http_status": None, "rows": 0,
             "sha256": None, "bytes": 0, "error_type": None,
             "retrieved_at_jst": None}
    try:
        req = Request(url, headers={"User-Agent": "BOAT-EDGE/1.0 PRE_RESULT diagnostic"})
        with urlopen(req, timeout=25) as response:
            raw = response.read()
            entry["http_status"] = response.status
            entry["retrieved_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
        entry["bytes"] = len(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows = list(reader)
        entry["rows"] = len(rows)
        entry["race_code_rows"] = sum(bool(str(r.get("レースコード") or "").strip()) for r in rows)
        entry["current_day_race_code_rows"] = sum(
            str(r.get("レースコード") or "").strip().startswith(now.strftime("%Y%m%d"))
            for r in rows)
        entry["csv_headers"] = list(reader.fieldnames or [])
    except HTTPError as exc:
        entry["http_status"] = exc.code
        entry["error_type"] = "HTTP_NOT_PUBLISHED" if exc.code == 404 else "HTTP_ERROR"
    except (URLError, TimeoutError, UnicodeError, csv.Error, OSError) as exc:
        entry["error_type"] = type(exc).__name__
    entry["availability_class"] = ("published_with_rows" if entry["http_status"] == 200 and entry["rows"] > 0 else
                                   "published_empty" if entry["http_status"] == 200 else
                                   "not_published_http_404" if entry["http_status"] == 404 else
                                   "http_or_transport_error")
    report["sources"][role] = entry
Path("fresh_csv_diagnostic.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, sort_keys=True))
