"""Manually triggered research-only capture; never publishes race data."""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from official_prerace_capture import capture_beforeinfo, save_raw_receipt, read_raw_receipt
from official_beforeinfo_inspect import inspect_saved_beforeinfo


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
    return {
        "race_key": race_key,
        "receipt_sha256": receipt["sha256"],
        "archive_files": [Path(path).name for path in paths],
        "diagnostic": diagnostic,
        "status": "unverified_raw_only",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-key", required=True)
    parser.add_argument("--deadline", required=True, help="Official race deadline ISO8601 with UTC offset")
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.race_key, args.deadline, args.directory), ensure_ascii=False))
