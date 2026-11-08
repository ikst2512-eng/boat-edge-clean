"""Read-only replay of four-mode capture artifact ZIPs (no network or writes).

Local GitHub artifact/receipt integrity and source-based exclusion accounting
are NOT independent remote first-seen, official T-12, or formal forecasts.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZipFile, BadZipFile

JST = timezone(timedelta(hours=9))
RAW_PREFIX = "four-mode-evidence/raw-sources/"
RAW_ID = re.compile(r"[0-9a-f]{64}")
CODE = re.compile(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])")
CSV_URL = re.compile(r"https://boatracecsv\.github\.io/data/programs/(title|race_cards)/(20\d{2})/(\d{2})/(\d{2})\.csv")
API_URL = re.compile(r"https://boatraceopenapi\.github\.io/api/v1/(20\d{2})/(20\d{6})\.json")
MAX_ZIP_BYTES = 4_000_000
MAX_ENTRY_BYTES = 2_000_000
MAX_TOTAL_UNCOMPRESSED = 8_000_000
MAX_ARCHIVE_ENTRIES = 128


def _load_json(value):
    return json.loads(value.decode("utf-8"))


def _source_rows(raw, kind, day):
    if kind == "race_cards":
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        result = {}
        for row in rows:
            code = row.get("レースコード", "")
            if not CODE.fullmatch(code) or not code.startswith(day) or code in result:
                raise ValueError("invalid_or_duplicate_source_race_code")
            rates = [float(row[f"艇{i}_全国勝率"]) for i in range(1, 7)]
            result[code] = {"rates": rates}
        return result
    if kind == "title":
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        result = {}
        for row in rows:
            code = row.get("レースコード", "")
            if not CODE.fullmatch(code) or not code.startswith(day) or code in result:
                raise ValueError("invalid_or_duplicate_source_race_code")
            result[code] = {"deadline": datetime.strptime(
                day + row["電話投票締切予定"], "%Y%m%d%H:%M").replace(tzinfo=JST)}
        return result
    if kind == "openapi":
        obj = _load_json(raw)
        stadiums = obj["programs"]["stadiums"]
        result = {}
        for sid, stadium in stadiums.items():
            for race_no, race in stadium["races"].items():
                code = day + f"{int(sid):02d}{int(race_no):02d}"
                if not CODE.fullmatch(code) or code in result or race.get("date", "").replace("-", "") != day:
                    raise ValueError("invalid_or_duplicate_source_race_code")
                racers = race["racers"]
                if set(racers) != set("123456"):
                    raise ValueError("incomplete_six_lanes")
                rates = [float(racers[str(i)]["national_win_rate"]) for i in range(1, 7)]
                deadline = datetime.fromisoformat(race["closed_at"])
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=JST)
                if deadline.astimezone(JST).strftime("%Y%m%d") != day:
                    raise ValueError("wrong_source_deadline_date")
                result[code] = {"rates": rates, "deadline": deadline}
        return result
    raise ValueError("unrecognized_source_kind")


def audit_zip(data, expected_zip_sha256):
    """Fail closed unless raw sources fully explain saved, cutoff, and invalids."""
    if not isinstance(data, bytes) or len(data) > MAX_ZIP_BYTES:
        raise ValueError("invalid_or_oversize_artifact")
    actual_sha = hashlib.sha256(data).hexdigest()
    if not isinstance(expected_zip_sha256, str) or not RAW_ID.fullmatch(expected_zip_sha256) or actual_sha != expected_zip_sha256:
        raise ValueError("artifact_digest_mismatch")
    try:
        with ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or any(n.startswith("/") or ".." in n.split("/") for n in names):
                raise ValueError("duplicate_or_unsafe_artifact_paths")
            members = z.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES or sum(i.file_size for i in members) > MAX_TOTAL_UNCOMPRESSED:
                raise ValueError("oversize_or_excessive_artifact_entries")
            if any(i.file_size > MAX_ENTRY_BYTES for i in members):
                raise ValueError("oversize_artifact_member")
            # Every archived local HTTP receipt needs exactly one JSON manifest
            # and one raw-byte member. A stray payload must never be ignored.
            raw_names = [n for n in names if n.startswith(RAW_PREFIX)]
            if (any(not re.fullmatch(re.escape(RAW_PREFIX) + r"[0-9a-f]{64}\.(?:json|bin)", n)
                    for n in raw_names)
                    or {n[:-5] for n in raw_names if n.endswith(".json")}
                    != {n[:-4] for n in raw_names if n.endswith(".bin")}):
                raise ValueError("unpaired_or_unexpected_raw_receipts")
            log = _load_json(z.read("four-mode-evidence/capture.log"))
            status = _load_json(z.read("four_mode_forecasts/capture_status.json"))
            day = status["day_jst"]
            datetime.strptime(day, "%Y%m%d")
            if status.get("source_status") != "available" or log.get("date_jst") != day:
                raise ValueError("source_unavailable_or_day_mismatch")
            source = {}
            receipts = []
            for name in names:
                if not name.startswith(RAW_PREFIX) or not name.endswith(".json"):
                    continue
                stem = name[len(RAW_PREFIX):-5]
                if not RAW_ID.fullmatch(stem):
                    raise ValueError("invalid_receipt_name")
                meta = _load_json(z.read(name))
                raw_name = RAW_PREFIX + stem + ".bin"
                raw = z.read(raw_name)
                if (meta.get("schema") != "FOUR_MODE_LOCAL_RAW_HTTP_RECEIPT_V1"
                        or meta.get("byte_count") != len(raw)
                        or meta.get("sha256") != hashlib.sha256(raw).hexdigest()):
                    raise ValueError("raw_http_receipt_mismatch")
                # Writer names the file by SHA256(URL + NUL + exact raw bytes).
                # Verify that content address, not just a self-reported digest.
                url = meta.get("url", "")
                if (type(url) is not str or hashlib.sha256(
                        url.encode("utf-8") + b"\0" + raw).hexdigest() != stem):
                    raise ValueError("raw_receipt_content_address_mismatch")
                received = datetime.fromisoformat(meta["received_at_jst"])
                if received.tzinfo is None or received.astimezone(JST).strftime("%Y%m%d") != day:
                    raise ValueError("invalid_source_receipt_date")
                csv_match = CSV_URL.fullmatch(url)
                api_match = API_URL.fullmatch(url)
                if csv_match:
                    kind, year, month, date = csv_match.groups()
                    if year + month + date != day:
                        raise ValueError("source_url_day_mismatch")
                elif api_match:
                    year, d = api_match.groups()
                    if d != day or year != day[:4]:
                        raise ValueError("source_url_day_mismatch")
                    kind = "openapi"
                else:
                    raise ValueError("unknown_raw_source_url")
                if kind in source:
                    raise ValueError("duplicate_raw_source_kind")
                source[kind] = _source_rows(raw, kind, day)
                receipts.append(received)
            if not receipts:
                raise ValueError("no_raw_source_receipts")
    except (BadZipFile, KeyError, UnicodeError, TypeError, OverflowError) as exc:
        raise ValueError("malformed_capture_artifact") from exc

    if set(source) == {"title", "race_cards"}:
        if source["title"].keys() != source["race_cards"].keys():
            raise ValueError("title_card_roster_mismatch")
        races = {k: {**source["title"][k], **source["race_cards"][k]}
                 for k in source["title"]}
        source_kind = "published_csv"
    elif set(source) == {"openapi"}:
        races = source["openapi"]
        source_kind = "nonofficial_openapi"
    else:
        raise ValueError("unsupported_raw_source_pair")
    if not races:
        raise ValueError("empty_source_roster")
    for row in races.values():
        if (len(row["rates"]) != 6 or not all(math.isfinite(v) and 0 <= v <= 10 for v in row["rates"])):
            raise ValueError("invalid_source_rate_not_zero")
    latest_receipt = max(receipts)
    cutoff = {k for k, row in races.items()
              if latest_receipt > row["deadline"] - timedelta(minutes=20)}
    zero = {k for k, row in races.items() if any(v == 0 for v in row["rates"])}
    saved_list = log["new_saved"]
    excluded_list = log["excluded_races"]
    saved = set(saved_list)
    excluded = {entry["race_code"] for entry in excluded_list}
    if (len(saved) != len(saved_list) or len(excluded) != len(excluded_list)
            or saved & excluded or not saved <= races.keys() or not excluded <= races.keys()):
        raise ValueError("invalid_saved_or_excluded_roster")
    if len(cutoff) != log["cutoff_skipped"] or saved & cutoff or excluded & cutoff:
        raise ValueError("cutoff_replay_mismatch")
    if source_kind == "published_csv":
        if (excluded != zero - cutoff or log["excluded"] != {"invalid six national win rates": len(excluded)}):
            raise ValueError("positive_rate_gate_exclusions_mismatch")
        openapi_rejected = 0
    else:
        if excluded or log["excluded"] or (saved | cutoff) != races.keys() - zero:
            raise ValueError("openapi_prefilter_reconciliation_failed")
        openapi_rejected = len(zero)
        probe = status["source_probes"]["openapi_direct"]
        if probe.get("rejected") != openapi_rejected or probe.get("valid") != len(races) - len(zero):
            raise ValueError("openapi_rejected_count_mismatch")
    missing = set(races) - saved - excluded - cutoff
    if missing != (zero - cutoff if source_kind == "nonofficial_openapi" else set()):
        raise ValueError("unexplained_source_missing_races")
    if (status["last_run_new_count"] != len(saved)
            or status["cutoff_skipped"] != len(cutoff)
            or status["excluded_races"] != excluded_list
            or status["already_saved"] != 0):
        raise ValueError("capture_status_disagrees_with_log")
    return {
        "schema": "FOUR_MODE_LOCAL_SOURCE_ARTIFACT_REPLAY_V1",
        "day_jst": day, "source_kind": source_kind,
        "archive_sha256": actual_sha, "source_receipts_sha256_checked": True,
        "raw_source_races": len(races), "locally_generated": len(saved),
        "cutoff_20m_reconstructed": len(cutoff), "source_zero_rate_races": len(zero),
        "model_zero_rate_exclusions": len(excluded),
        "openapi_zero_rate_prefilter_rejections": openapi_rejected,
        "zero_rate_races_also_cutoff_skipped": len(zero & cutoff),
        "unexplained_races": 0, "validated_research_audit_only": True,
        "independent_remote_first_seen_verified": False,
        "official_t12_certified": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("artifact", type=Path)
    p.add_argument("--expected-sha256", required=True)
    args = p.parse_args()
    result = audit_zip(args.artifact.read_bytes(), args.expected_sha256)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
