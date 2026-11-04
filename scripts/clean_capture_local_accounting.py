"""Read-only CLEAN collector accounting; local files are not Git publication proof.

A successful capture process produces a final one-line JSON object on stdout.
The freeze/push runs in another step, so these numbers never certify GitHub
first-add, a remote receipt, a formal forecast, or forecast accuracy.
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
SCHEMA = "CLEAN_CAPTURE_LOCAL_ACCOUNTING_V1"


def _report(status, day=None, eligible=None, new=None, frozen=None):
    return {
        "schema": SCHEMA,
        "status": status,
        "day_jst": day,
        "eligible_generated": eligible,
        "locally_created": new,
        "already_frozen": frozen,
        "git_first_add_verified": False,
        "remote_first_seen_verified": False,
        "formal": False,
        "scoring": False,
    }


def inspect_log(contents, expected_day):
    """Fail closed on absent/malformed/old summaries, without losing logs."""
    if not isinstance(expected_day, str) or not re.fullmatch(r"20[0-9]{6}", expected_day):
        raise ValueError("invalid_expected_day")
    datetime.strptime(expected_day, "%Y%m%d")
    if contents is None:
        return _report("capture_log_missing")
    if not isinstance(contents, str):
        raise TypeError("capture_log_must_be_text")
    # The collector prints its summary last. No other diagnostic JSON line
    # should be allowed to masquerade as its final returned result.
    lines = [line.strip() for line in contents.splitlines() if line.strip()]
    if not lines:
        return _report("capture_summary_missing")
    candidate = lines[-1]
    try:
        record = json.loads(candidate)
    except (ValueError, TypeError):
        return _report("capture_summary_missing")
    if not isinstance(record, dict):
        return _report("capture_summary_invalid")
    required = ("saved", "eligible", "already_frozen")
    if record.get("date") != expected_day:
        return _report("capture_day_unverified")
    if any(type(record.get(key)) is not int or record[key] < 0 for key in required):
        return _report("capture_summary_invalid", day=expected_day)
    new, eligible, frozen = (record["saved"], record["eligible"],
                             record["already_frozen"])
    if (eligible != new + frozen or record.get("formal_predictions") != 0
            or record.get("scoring_enabled") is not False):
        return _report("capture_summary_invalid", day=expected_day)
    return _report("local_capture_completed_not_git_proof",
                   day=expected_day, eligible=eligible, new=new, frozen=frozen)


def run(log_path, output_path, expected_day=None):
    day = expected_day or datetime.now(JST).strftime("%Y%m%d")
    log_path = Path(log_path)
    contents = log_path.read_text(encoding="utf-8") if log_path.is_file() else None
    report = inspect_log(contents, day)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    print("CLEAN_CAPTURE_LOCAL_ACCOUNTING=" + json.dumps(report, sort_keys=True))
    if report["status"] != "local_capture_completed_not_git_proof":
        print("::warning::CLEAN local capture completion not evidenced in this run")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-log", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.capture_log, args.output)
