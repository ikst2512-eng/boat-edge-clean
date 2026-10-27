"""Collect independently published post-race result CSV into immutable CLEAN records.

Read-only external CSV; writes CLEAN confirmed_results only. No legacy repo.
"""
import csv
import hashlib
import io
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
BASE = "https://boatracecsv.github.io/data/results/realtime/"
DATE_RE = re.compile(r"^[0-9]{8}$")
RACE_RE = re.compile(r"^[0-9]{8}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])$")


def build_records(day, raw, collected_at):
    if not DATE_RE.fullmatch(day):
        raise ValueError("date")
    datetime.strptime(day, "%Y%m%d")
    if len(raw) > 2_000_000:
        raise ValueError("source too large")
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    needed = {"レースコード", "取得日時", "1着_艇番", "2着_艇番", "3着_艇番"}
    if not reader.fieldnames or not needed.issubset(reader.fieldnames):
        raise ValueError("unrecognized result schema")
    digest = hashlib.sha256(raw).hexdigest()
    records = {}
    for row in reader:
        code = row.get("レースコード", "")
        if not isinstance(code, str) or not RACE_RE.fullmatch(code) or not code.startswith(day):
            continue
        if code in records:
            raise ValueError("duplicate source result")
        tokens = [str(row.get(f"{i}着_艇番", "")).strip() for i in (1, 2, 3)]
        # Canceled races, disqualifications, unfinished or joint finish must
        # not be converted into an ordinary trifecta.
        if not all(re.fullmatch(r"[1-6]", n) for n in tokens) or len(set(tokens)) != 3:
            continue
        source_time = row.get("取得日時", "")
        if not source_time:
            continue
        try:
            ts = datetime.fromisoformat(source_time.replace("Z", "+00:00"))
            if ts.utcoffset() is None:
                continue
        except ValueError:
            continue
        if ts > collected_at + timedelta(minutes=3):
            continue
        url = BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        records[code] = {
            "race_code": code, "status": "confirmed",
            "finish_order": [int(n) for n in tokens],
            "source_url": url,
            "source_sha256": digest,
            "confirmed_at_jst": ts.astimezone(JST).isoformat(),
            "collected_at_jst": collected_at.astimezone(JST).isoformat(),
            "provenance_note": "Published post-race CSV; confirmed_at_jst is source acquisition time, not an official adjudication timestamp",
        }
    return records


def collect(day=None):
    now = datetime.now(JST)
    day = day or now.strftime("%Y%m%d")
    if not DATE_RE.fullmatch(day):
        raise ValueError("invalid date")
    datetime.strptime(day, "%Y%m%d")
    url = BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
    try:
        with urlopen(Request(url, headers={"User-Agent": "BOAT-EDGE-CLEAN-RESULTS/1.0"}), timeout=15) as response:
            if response.status != 200:
                raise ValueError("source unavailable")
            raw = response.read(2_000_001)
    except HTTPError as exc:
        if exc.code == 404:
            return {"day": day, "source_races": 0, "saved": 0, "status": "waiting_for_published_source", "http_status": 404, "source_url": url}
        raise
    records = build_records(day, raw, now)
    target = ROOT / "confirmed_results"
    saved = 0
    for code, record in sorted(records.items()):
        target.mkdir(exist_ok=True)
        file = target / (code + ".json")
        if file.is_symlink():
            raise ValueError("symlink record refused")
        if file.exists():
            existing = json.loads(file.read_text(encoding="utf-8"))
            if existing.get("race_code") != code or existing.get("status") != "confirmed":
                raise ValueError("existing archive invalid")
            if existing.get("finish_order") != record["finish_order"]:
                raise ValueError("published finish order changed; manual review required")
            continue
        try:
            with file.open("x", encoding="utf-8") as out:
                json.dump(record, out, ensure_ascii=False, sort_keys=True)
                out.flush()
                os.fsync(out.fileno())
            saved += 1
        except FileExistsError:
            continue
    return {"day": day, "source_races": len(records), "saved": saved}


def collect_recent(now=None, collector=collect):
    """Retry yesterday as well as today; source 404 is pending, not a miss."""
    now = now or datetime.now(JST)
    dates = [(now-timedelta(days=1)).strftime("%Y%m%d"), now.strftime("%Y%m%d")]
    return {"status": "checked", "days": [collector(day) for day in dates]}


if __name__ == "__main__":
    print(json.dumps(collect_recent(), ensure_ascii=False))
