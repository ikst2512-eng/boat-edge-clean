"""Manually triggered research-only capture; never publishes race data."""
import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from official_prerace_capture import capture_beforeinfo, save_raw_receipt, read_raw_receipt
from official_beforeinfo_inspect import inspect_saved_beforeinfo
from official_beforeinfo_research_parser import research_saved_start_exhibition


def run(race_key, deadline_text, directory):
    try:
        deadline = datetime.fromisoformat(deadline_text)
    except ValueError as exc:
        raise ValueError("deadline must be ISO8601 with timezone") from exc
    if deadline.tzinfo is None or deadline.utcoffset() != timedelta(hours=9):
        raise ValueError("official deadline must include JST +09:00 offset")
    receipt, raw = capture_beforeinfo(race_key, deadline)
    paths = save_raw_receipt(receipt, raw, directory, deadline=deadline)
    read_raw_receipt(directory, race_key, receipt["sha256"], deadline=deadline)
    diagnostic = inspect_saved_beforeinfo(directory, race_key, receipt["sha256"], deadline=deadline)
    if (diagnostic.get("status") != "inspection_only"
            or diagnostic.get("race_key") != race_key
            or diagnostic.get("verified_preview") is not False
            or diagnostic.get("actual_entry_verified") is not False
            or diagnostic.get("racers") != []
            or diagnostic.get("start_exhibition") != []):
        raise ValueError("unsafe diagnostic: cannot publish verified or raced data")
    try:
        research = research_saved_start_exhibition(directory, race_key, receipt["sha256"], deadline=deadline)
    except (ValueError, UnicodeError) as exc:
        research = {"status": "research_unavailable", "reason": type(exc).__name__,
                    "verified_preview": False, "actual_entry_verified": False,
                    "start_exhibition": []}
    if research.get("status") == "research_unverified":
        rows = research.get("start_exhibition")
        if (research.get("race_key") != race_key
                or research.get("raw_sha256") != receipt["sha256"]
                or research.get("captured_at") != receipt["fetched_at"]
                or research.get("verified_preview") is not False
                or research.get("actual_entry_verified") is not False
                or not isinstance(rows, list) or len(rows) != 6
                or any(not isinstance(row, dict) for row in rows)
                or any(type(row.get("boat_number")) is not int for row in rows)
                or any(type(row.get("exhibition_course")) is not int for row in rows)
                or any(type(row.get("exhibition_st")) not in (int, float)
                       or not -1 < row["exhibition_st"] < 1 for row in rows)
                or sorted(row["boat_number"] for row in rows) != list(range(1, 7))
                or [row.get("exhibition_course") for row in rows] != list(range(1, 7))):
            raise ValueError("research provenance or six-boat integrity mismatch")
    elif (research.get("status") != "research_unavailable"
          or research.get("verified_preview") is not False
          or research.get("actual_entry_verified") is not False
          or research.get("start_exhibition") != []):
        raise ValueError("research result cannot be promoted")
    result = {
        "race_key": race_key,
        "receipt_sha256": receipt["sha256"],
        "official_source": receipt["source"],
        "fetched_at": receipt["fetched_at"],
        "deadline": deadline.isoformat(),
        "archive_files": [Path(path).name for path in paths],
        "diagnostic": diagnostic,
        "research_extraction": research,
        "status": "unverified_raw_only",
    }
    # Publish the provenance summary with the archive, not only in ephemeral logs.
    manifest = Path(directory) / (race_key + "-" + receipt["sha256"] + ".manifest.json")
    # Serialize completely and durably before publishing the manifest name.
    payload = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    pending = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".manifest-pending-",
                                         delete=False) as handle:
            pending = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(pending, manifest)  # fails closed if this manifest already exists
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-key", required=True)
    parser.add_argument("--deadline", required=True, help="Official race deadline ISO8601 with UTC offset")
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.race_key, args.deadline, args.directory), ensure_ascii=False))
