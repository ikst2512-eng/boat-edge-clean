"""Read-only Git ancestry audit for the Nov 4+ third-place V2 shadow cohort.

A Git commit's timestamp is NOT an independently witnessed remote first-seen
time. Never call this a formal prospective cohort or promote the model.
"""
import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from scripts.audit_four_mode_daily_main_archives import parse_additions

FUTURE_START = "20261104"
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
NAME = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, timeout=30)


def audit(root, *, git=_git):
    root = Path(root)
    result = {
        "status": "read_only_git_ancestry_research",
        "future_start_jst": FUTURE_START,
        "independent_remote_first_seen_verified": False,
        "independent_cutoff_publication_verified": False,
        "untouched_external_holdout_verified": False,
        "formal": False,
        "production_promotion_allowed": False,
        "checkout_git_history_complete": False,
        "checked_future_archive_count": 0,
        "future_result_paired": 0,
        "future_result_paired_race_codes": [],
        "first_add_before_t_minus_12_count": 0,
        "first_add_after_t_minus_12_count": 0,
        "first_add_original_blob_mismatch_count": 0,
        "missing_or_ambiguous_first_add_count": 0,
        "unverifiable_count": 0,
        "by_day": {},
        "rows": [],
        "warning": "Git committer dates and initial blob consistency are only local ancestry checks, NOT independently verified remote publication.",
    }
    folder = root / "four_mode_forecasts"
    if not folder.is_dir():
        result["status"] = "no_forecast_directory"
        return result
    paths = sorted(p for p in folder.glob("*.json")
                   if NAME.fullmatch("four_mode_forecasts/" + p.name)
                   and p.stem[:8] >= FUTURE_START)
    result["checked_future_archive_count"] = len(paths)
    if not paths:
        result["status"] = "no_future_v2_archives"
        return result
    try:
        shallow = git(root, "rev-parse", "--is-shallow-repository").decode().strip()
        if shallow != "false":
            result["status"] = "incomplete_git_history"
            result["unverifiable_count"] = len(paths)
            return result
        additions = parse_additions(git(
            root, "log", "--diff-filter=A", "--format=%H", "--name-only",
            "HEAD", "--", "four_mode_forecasts/").decode())
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        result["status"] = "git_history_unavailable"
        result["unverifiable_count"] = len(paths)
        return result
    result["checkout_git_history_complete"] = True
    commit_times = {}
    counter = Counter()
    for path in paths:
        code = path.stem
        name = "four_mode_forecasts/" + path.name
        entry = {"race_code": code, "first_add_commit_sha": None,
                 "first_add_commit_jst": None, "deadline_jst": None,
                 "t_minus_12_jst": None, "paired_result": False,
                 "status": "unverifiable"}
        record_status, archive = archived_four_modes(code, root)
        if record_status != 200 or archive.get("model_version") != VERSION:
            entry["status"] = "invalid_v2_archive"
        elif path.is_symlink() or path.stat().st_size > 30000:
            entry["status"] = "unsafe_file"
        else:
            outcome = compare_race(code, root)
            entry["paired_result"] = outcome.get("status") == "historical_comparison_only"
            result["future_result_paired"] += int(entry["paired_result"])
            if entry["paired_result"]:
                result["future_result_paired_race_codes"].append(code)
            try:
                deadline = datetime.fromisoformat(archive["deadline_jst"])
                cutoff = deadline - timedelta(minutes=12)
                entry["deadline_jst"] = deadline.isoformat()
                entry["t_minus_12_jst"] = cutoff.isoformat()
                shas = additions.get(name, [])
                if len(shas) != 1 or not SHA.fullmatch(shas[0]):
                    entry["status"] = "missing_or_ambiguous_first_add"
                else:
                    sha = shas[0]
                    entry["first_add_commit_sha"] = sha
                    if sha not in commit_times:
                        timestamp = git(root, "show", "-s", "--format=%cI", sha).decode().strip()
                        stamp = datetime.fromisoformat(timestamp)
                        if stamp.utcoffset() is None:
                            raise ValueError("naive commit timestamp")
                        commit_times[sha] = stamp
                    first_add_time = commit_times[sha]
                    entry["first_add_commit_jst"] = first_add_time.isoformat()
                    original = git(root, "show", sha + ":" + name)
                    current = path.read_bytes()
                    if original != current:
                        entry["status"] = "changed_since_git_first_add"
                    elif first_add_time > cutoff:
                        entry["status"] = "git_first_add_after_t_minus_12"
                    else:
                        entry["status"] = "git_first_add_before_t_minus_12"
            except (OSError, ValueError, TypeError, subprocess.SubprocessError):
                entry["status"] = "unverifiable"
        counter[entry["status"]] += 1
        day = code[:8]
        daily = result["by_day"].setdefault(day, {
            "forecasts": 0, "paired_result": 0, "git_first_add_pre_t12": 0,
        })
        daily["forecasts"] += 1
        daily["paired_result"] += int(entry["paired_result"])
        daily["git_first_add_pre_t12"] += int(
            entry["status"] == "git_first_add_before_t_minus_12")
        result["rows"].append(entry)
    result["first_add_before_t_minus_12_count"] = counter["git_first_add_before_t_minus_12"]
    result["first_add_after_t_minus_12_count"] = counter["git_first_add_after_t_minus_12"]
    result["first_add_original_blob_mismatch_count"] = counter["changed_since_git_first_add"]
    result["missing_or_ambiguous_first_add_count"] = counter["missing_or_ambiguous_first_add"]
    result["unverifiable_count"] = sum(v for key, v in counter.items()
                                       if key in ("unverifiable", "invalid_v2_archive", "unsafe_file"))
    if sum(counter.values()) != len(paths):
        raise ValueError("first_add_status_partition")
    if sum(row["paired_result"] for row in result["rows"]) != result["future_result_paired"]:
        raise ValueError("future_paired_partition")
    if (result["future_result_paired_race_codes"] != sorted(set(
            result["future_result_paired_race_codes"])) or
            len(result["future_result_paired_race_codes"]) != result["future_result_paired"]):
        raise ValueError("future_paired_roster_partition")
    result["by_day"] = dict(sorted(result["by_day"].items()))
    return result


def verify_shadow_cohort(audit_result, shadow_result):
    """Require exact race-code identity, never just equal cohort sizes.

    Local Git archive presence cannot promote independently verified evidence.
    """
    future = shadow_result["date_separated_forward_reference"]
    shadow_codes = future.get("paired_race_codes")
    audit_codes = audit_result.get("future_result_paired_race_codes")
    if (future.get("start_day_jst") != FUTURE_START
            or type(future.get("paired")) is not int
            or type(audit_result.get("future_result_paired")) is not int
            or not isinstance(shadow_codes, list)
            or not isinstance(audit_codes, list)
            or audit_result["future_result_paired"] != future["paired"]):
        raise ValueError("forward_result_cohort_mismatch")
    for codes, count in ((shadow_codes, future["paired"]),
                         (audit_codes, audit_result["future_result_paired"])):
        if (len(codes) != count or
                any(type(code) is not str or
                    not re.fullmatch(r"20[0-9]{10}", code) or
                    code[:8] < FUTURE_START for code in codes) or
                codes != sorted(set(codes))):
            raise ValueError("invalid_forward_race_roster")
    if audit_codes != shadow_codes:
        raise ValueError("forward_race_identity_mismatch")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = audit(Path(__file__).resolve().parent)
    if args.shadow_log is not None:
        lines = args.shadow_log.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line.split("V2_THIRD_RATE_SHADOW=", 1)[1])
                  for line in lines if line.startswith("V2_THIRD_RATE_SHADOW=")]
        if len(values) != 1:
            raise ValueError("missing_or_duplicated_shadow_report")
        output["shadow_future_result_cohort_reconciled"] = verify_shadow_cohort(
            output, values[0])
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")
    print("V2_THIRD_RATE_GIT_ANCESTRY=" + json.dumps(output, sort_keys=True))
