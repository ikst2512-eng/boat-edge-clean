"""Manual, result-blind, research-only capture driver.

This is *not* a scheduler or independent first-receipt service. An explicit
manual gateway on the default branch, if separately reviewed and merged,
can call this exact pinned source code in a read-only checkout. Never read
confirmed_results; never write GitHub branches; do not promote to formal.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from hole_future_pair_precommit import JST, freeze
from research.hole_pair_universe_coverage import canonical_json, reconcile

RACE_PATH = re.compile(r"four_mode_forecasts/(20\d{10})\.json\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
ACK = "CAPTURE_UNVERIFIED_RESEARCH"
EXCLUSION_REASONS = frozenset({
    "after_t_minus_12", "source_not_generated_before_freeze",
    "archive_unavailable_or_invalid", "invalid_deadline",
    "calculation_crossed_t_minus_12",
})


def _git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.PIPE)


def capture(day, source_sha, paths, read_source, read_blob, freezer,
            root, *, current_time, start_time=None, finish_time=None):
    """Collect exactly one immutable source-main snapshot, without outcomes."""
    if (type(day) is not str or not re.fullmatch(r"20\d{6}", day)
            or day < "20261109" or current_time.tzinfo is None
            or current_time.utcoffset() != JST.utcoffset(None)
            or current_time.strftime("%Y%m%d") != day):
        raise ValueError("capture_day_not_current_future_jst")
    if type(source_sha) is not str or not SHA40.fullmatch(source_sha):
        raise ValueError("untrusted_main_source_commit")
    if (type(paths) is not list or len(paths) > 500 or
            len(set(paths)) != len(paths)):
        raise ValueError("unsafe_or_duplicate_source_paths")
    expected = sorted(paths)
    if paths != expected:
        raise ValueError("source_paths_not_sorted")
    root = Path(root)
    records, excluded = [], collections.Counter()
    exclusions = collections.defaultdict(list)
    codes = []
    started = start_time or current_time
    for path in paths:
        match = RACE_PATH.fullmatch(path)
        if not match or not path.startswith("four_mode_forecasts/" + day):
            raise ValueError("untrusted_source_path")
        code = match.group(1)
        codes.append(code)
        raw = read_source(path)
        if type(raw) is not bytes or len(raw) > 30000:
            raise ValueError("unsafe_original_forecast_bytes")
        blob = read_blob(path)
        if type(blob) is not str or not SHA40.fullmatch(blob):
            raise ValueError("untrusted_main_forecast_blob")
        expected_blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        if expected_blob != blob:
            raise ValueError("immutable_main_source_blob_content_mismatch")
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            raise ValueError("unsafe_forecast_symlink")
        if target.exists():
            if not target.is_file() or target.read_bytes() != raw:
                raise ValueError("research_checkout_has_conflicting_forecast")
        else:
            target.write_bytes(raw)
        result = freezer(code, root)
        if type(result) is not dict or result.get("race_code") != code:
            raise ValueError("invalid_freezer_output_identity")
        status = result.get("status")
        if status == "locally_frozen_unverified":
            if "source_git_blob_sha1" in result:
                raise ValueError("unexpected_prepopulated_original_blob")
            if result.get("source_sha256") != hashlib.sha256(raw).hexdigest():
                raise ValueError("frozen_candidate_original_source_sha256_mismatch")
            result["source_git_blob_sha1"] = blob
            records.append(result)
        elif status in EXCLUSION_REASONS:
            excluded[status] += 1
            exclusions[status].append(code)
        else:
            raise ValueError("unknown_freezer_exclusion_reason")
    finished = finish_time or datetime.now(JST)
    if (finished.tzinfo is None or finished.utcoffset() != JST.utcoffset(None)
            or finished < started or finished.strftime("%Y%m%d") != day):
        raise ValueError("capture_crossed_day_or_clock_reversed")
    # The existing reconciliation enforces every original ID exactly once,
    # frozen method/selector provenance and protected Top5 coverage.
    coverage = reconcile(day, source_sha, codes, records, dict(exclusions))
    if coverage["excluded_by_reason"] != dict(sorted(excluded.items())):
        raise ValueError("excluded_counter_or_membership_mismatch")
    return {
        "schema": "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1",
        "status": "local_predeadline_freeze_not_formal",
        "source_main_commit": source_sha,
        "capture_day_jst": day,
        "batch_started_at_jst": started.isoformat(),
        "batch_finished_at_jst": finished.isoformat(),
        "eligible_forecasts_examined": len(paths),
        "frozen_count": len(records),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "source_forecast_codes": codes,
        "excluded_race_codes_by_reason": coverage["excluded_race_codes_by_reason"],
        "source_snapshot_coverage": coverage,
        "records": records,
        "formal": False,
        "prospective_validation": False,
        "independent_first_receipt_verified": False,
        "production_forecast_changed": False,
        "warning": (
            "Manual local pre-cutoff research only; no independent first remote "
            "receipt, external signed time, or official six-boat/120-odds T-12 "
            "completeness proof. Not formal, not a production selector."
        ),
    }


def manual_only_guard(day, event_name, acknowledgment):
    if event_name != "workflow_dispatch" or acknowledgment != ACK:
        raise ValueError("manual_research_dispatch_not_authorized")
    if type(day) is not str or not re.fullmatch(r"20\d{6}", day):
        raise ValueError("invalid_capture_day")
    # Official outcomes/archived Nov6–8 cannot be reopened as future freeze.
    now = datetime.now(JST)
    if day != now.strftime("%Y%m%d") or day < "20261109":
        raise ValueError("backdated_or_noncurrent_capture_day")
    return now


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture-day", required=True)
    p.add_argument("--output", default="research_candidate_freeze.json")
    args = p.parse_args()
    now = manual_only_guard(args.capture_day,
                            os.getenv("GITHUB_EVENT_NAME"),
                            os.getenv("HOLE_RESEARCH_MANUAL_ACK"))
    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise ValueError("cannot_overwrite_existing_candidate_artifact")
    # Read the exact fetched main commit, never mutable ongoing files or results.
    head = _git("rev-parse", "origin/main").decode().strip()
    names = _git("ls-tree", "-r", "--name-only", head,
                 "--", "four_mode_forecasts/").decode().splitlines()
    day_paths = sorted(
        pth for pth in names
        if pth.startswith("four_mode_forecasts/" + args.capture_day)
        and pth.endswith(".json")
    )
    def read_source(path):
        return _git("show", head + ":" + path)
    def read_blob(path):
        return _git("rev-parse", head + ":" + path).decode().strip()
    manifest = capture(args.capture_day, head, day_paths, read_source,
                       read_blob, freeze, ".", current_time=now,
                       start_time=now)
    output.write_text(canonical_json(manifest), encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"], "frozen": manifest["frozen_count"],
        "excluded": manifest["excluded_by_reason"],
        "source_main_commit": head, "formal": False,
        "independent_first_receipt_verified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
