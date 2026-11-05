"""Read-only 2026-11-05 exact-main historical four-mode outcome audit.

This cannot certify first Git-add or first remote receipt, nor imply that
nightly collection coverage is complete. Uses ORIGINAL saved tickets plus
separately stored result content. No ticket generation or model changes.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import summarize_group
from four_mode_research_batch import MODES

DAY = "20261105"
SHA = re.compile(r"[0-9a-f]{40}\Z")
CODE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
TOPS = ("top1", "top3", "top5", "top10")
JST = timedelta(hours=9)
FOLDERS = ("four_mode_forecasts", "confirmed_results", "prospective_predictions")


def inventory(root, git=None):
    """Pin to actual checked-out commit and compare Git filenames only."""
    root = Path(root)
    git = git or (lambda args: subprocess.check_output(
        ["git", *args], cwd=root, timeout=35))
    head = git(["rev-parse", "--verify", "HEAD"])
    if type(head) is not bytes or SHA.fullmatch(head.decode("ascii").strip()) is None:
        raise ValueError("unverified_main_checkout_sha")
    sha = head.decode("ascii").strip()
    raw = git(["ls-tree", "-r", "-z", sha, "--", *FOLDERS])
    if type(raw) is not bytes or len(raw) > 16_000_000:
        raise ValueError("invalid_git_tree")
    sets = {name: set() for name in FOLDERS}
    seen = set()
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        try:
            attrs, path = entry.split(b"\t", 1)
            mode, kind, obj = attrs.decode("ascii").split(" ")
            path = path.decode("ascii")
        except (UnicodeError, ValueError) as exc:
            raise ValueError("invalid_git_tree_entry") from exc
        if (mode != "100644" or kind != "blob" or SHA.fullmatch(obj) is None
                or path in seen or path.startswith("/") or ".." in path.split("/")):
            raise ValueError("unsafe_or_duplicate_git_tree_entry")
        seen.add(path)
        folder, sep, name = path.partition("/")
        if (not sep or folder not in sets or "/" in name
                or not name.endswith(".json")):
            continue
        code = name[:-5]
        if CODE.fullmatch(code) and code.startswith(DAY):
            sets[folder].add(code)
    return sha, sets


def _local_source_t12_status(code, root):
    """Local chronology check only; explicit nonremote diagnostic."""
    path = Path(root) / "four_mode_forecasts" / (code + ".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 30000:
        return "unreadable_original"
    try:
        data = json.loads(path.read_bytes())
        if (type(data) is not dict or data.get("race_code") != code
                or data.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"):
            raise ValueError("archive_identity_mismatch")
        values = []
        for field in ("source_title_received_jst", "source_cards_received_jst",
                      "generated_at_jst", "deadline_jst"):
            when = datetime.fromisoformat(data[field])
            if when.utcoffset() != JST:
                raise ValueError("not_JST")
            values.append(when)
        title, cards, generated, deadline = values
        if deadline.strftime("%Y%m%d") != code[:8]:
            raise ValueError("wrong_deadline_date")
        cutoff = deadline - timedelta(minutes=12)
        return ("local_claimed_T_minus_12_consistent"
                if max(title, cards) <= generated < cutoff
                else "local_claimed_T_minus_12_inconsistent")
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            OverflowError, UnicodeError):
        return "unverifiable_local_source_time"


def run(root, git=None, comparator=compare_race, summarizer=summarize_group):
    root = Path(root)
    sha, items = inventory(root, git=git)
    four = items["four_mode_forecasts"]
    results = items["confirmed_results"]
    clean = items["prospective_predictions"]
    common = sorted(four & results)
    only_four = sorted(four - results)
    only_results = sorted(results - four)
    local_timing = Counter(_local_source_t12_status(code, root)
                           for code in sorted(four))
    validated = []
    exclusions = []
    for code in common:
        try:
            record = comparator(code, root)
        except (OSError, ValueError, KeyError, TypeError, AttributeError,
                UnicodeError) as exc:
            record = {"status": "comparison_exception_" + type(exc).__name__}
        if (type(record) is dict
                and record.get("race_code") == code
                and record.get("status") == "historical_comparison_only"
                and record.get("formal") is False
                and record.get("remote_first_seen_verified") is False):
            validated.append(code)
        else:
            exclusions.append({"race_code": code, "reason": (
                record.get("status", "unknown_status")
                if type(record) is dict else "non_object_comparison")})
    complete = bool(common) and len(validated) == len(common)
    summary = summarizer(validated, root, include_per_race=True) if validated else None
    if summary and (summary["historical_comparable"] != len(validated)
                    or len(summary["per_race"]) != len(validated)
                    or {r["race_code"] for r in summary["per_race"]} != set(validated)):
        raise ValueError("validated_roster_mismatch_after_rescoring")
    # Never promote partial or malformed saved outcomes into cohort hit rates.
    hits = summary["topn_hits"] if complete else None
    rates = ({mode: {key: round(hits[mode][key] * 100 / len(common), 2)
                     for key in TOPS} for mode in MODES} if complete else None)
    misses = None
    if complete:
        misses = {m: dict(Counter(row["modes"][m]["coverage_diagnostic"]
                    for row in summary["per_race"])) for m in MODES}
    code_digest = hashlib.sha256(
        ("\n".join(common) + "\n").encode("ascii")).hexdigest()
    return {
        "schema": "FOUR_MODE_NOV05_MAIN_SNAPSHOT_HISTORICAL_AUDIT_V1",
        "status": ("main_snapshot_research_comparable" if complete
                   else "incomplete_saved_result_contents"),
        "day_jst": DAY, "examined_main_sha": sha,
        "main_tree_file_rosters_scanned": True,
        "four_mode_original_files": len(four),
        "clean_separate_original_files": len(clean),
        "independent_result_filenames": len(results),
        "four_mode_result_filename_intersection": len(common),
        "intersection_sha256": code_digest,
        "intersection_race_codes": common,
        "forecasts_without_result_filename": only_four,
        "result_filenames_without_four_mode": only_results,
        "result_content_comparable_count": len(validated),
        "untrusted_or_invalid_result_rows": exclusions,
        "local_source_t12_diagnostic_only": dict(local_timing),
        "historical_topn_hits": hits,
        "historical_topn_pct": rates,
        "historical_pairwise_topn": (
            summary["pairwise_topn"] if complete else None),
        "historical_coverage_miss_reasons": misses,
        "historical_per_race": summary["per_race"] if complete else None,
        "formal": False, "prospective_accuracy_verified": False,
        "first_git_add_chronology_verified": False,
        "github_remote_receipt_verified": False,
        "collection_run_inventory_verified": False,
        "model_improvement_proven": False,
        "production_forecast_changed": False,
        "warning": ("A frozen main Git snapshot compared retrospectively with "
                    "independently stored result CONTENT (not remote receipt). "
                    "Exact historical hit coverage is not formal/prospective accuracy. "
                    "Main-tree membership says nothing about skipped collection "
                    "runs, external original receipt or 6-boat official beforeinfo.")
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--main-root", type=Path, required=True)
    p.add_argument("--output", default="nov05_four_mode_snapshot_audit.json")
    args = p.parse_args()
    report = run(args.main_root)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("NOV05_FOUR_MODE_MAIN_SNAPSHOT=" + json.dumps({
        key: report[key] for key in
        ("status", "day_jst", "examined_main_sha", "four_mode_original_files",
         "clean_separate_original_files", "independent_result_filenames",
         "four_mode_result_filename_intersection",
         "result_content_comparable_count", "local_source_t12_diagnostic_only",
         "historical_topn_hits", "historical_topn_pct", "historical_coverage_miss_reasons")
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "main_snapshot_research_comparable" else 2


if __name__ == "__main__":
    raise SystemExit(main())
