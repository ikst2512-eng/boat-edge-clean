"""Read-only official-input *negative control* for the current four-mode shadow.

Test on exact Git original inputs whether replacing the absent official
beforeinfo flag and injecting distinctly FAKE official-like sentinel data
affects the existing, frozen candidate method. This is a code dependency
diagnostic ONLY, not official-data acquisition, candidate publication or
statistical performance. No result file is read and no selector is edited.
"""
import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from four_mode_all_mode_same_job_shadow import candidate_modes
from four_mode_nov09_main_original_input_readiness import (
    COMMIT, RACE_FILE, RESULT_KEYS, review_snapshot, sha1_blob,
)

SENTINEL = "TEST_ONLY_NOT_REAL_OFFICIAL_DATA"
REF = "refs/remotes/origin/main"


def negative_control(original):
    if (type(original) is not dict
            or RESULT_KEYS.intersection(original)
            or original.get("beforeinfo") != "optional_not_in_snapshot"
            or type(original.get("source_sha256")) is not dict
            or set(original["source_sha256"]) != {"race_cards", "title"}
            or any(k in original for k in (
                "official_beforeinfo", "official_exhibition", "official_odds_120"))):
        raise ValueError("not_official_feature_absent_original")
    baseline, candidate = candidate_modes(original)
    changed = copy.deepcopy(original)
    changed["beforeinfo"] = SENTINEL
    changed["official_beforeinfo"] = {"audit_only": SENTINEL}
    changed["official_exhibition"] = {"audit_only": SENTINEL}
    changed["official_odds_120"] = {"audit_only": SENTINEL}
    later_baseline, later_candidate = candidate_modes(changed)
    return {
        "original_baseline_unchanged": baseline == later_baseline,
        "candidate_tickets_unchanged_under_synthetic_official_controls":
            candidate == later_candidate,
    }


def examine(entries, day, commit):
    files = list(entries)
    baseline = review_snapshot(files, day, commit)
    if (baseline["valid_v2_original_inputs"] != len(files)
            or baseline["invalid_inputs"]):
        raise ValueError("original_git_blob_or_model_replay_incomplete")
    insensitive = 0
    for path, blob, raw in files:
        code = RACE_FILE.fullmatch(path).group(1)
        original = json.loads(raw)
        if original["race_code"] != code or sha1_blob(raw) != blob:
            raise ValueError("saved_original_identity_or_sha_mismatch")
        evidence = negative_control(original)
        if evidence["original_baseline_unchanged"] and evidence[
                "candidate_tickets_unchanged_under_synthetic_official_controls"]:
            insensitive += 1
    return {
        "schema": "FOUR_MODE_OFFICIAL_FEATURE_NEGATIVE_CONTROL_V1",
        "day": day, "pinned_main_commit": commit,
        "method": "frozen_existing_four_mode_all_mode_same_job_shadow_candidate_modes",
        "real_saved_origins_verified": len(files),
        "real_origins_beforeinfo_optional_not_in_snapshot": len(files),
        "only_race_cards_and_title_source_digests": len(files),
        "synthetic_negative_controls_in_memory_only": len(files),
        "mode_candidate_insensitive_to_synthetic_official_fields": insensitive,
        "real_official_source_data_read": False,
        "confirmed_results_read": False,
        "candidate_files_generated_or_written": False,
        "official_three_source_model_consumption_verified": False,
        "candidate_first_remote_receipt_verified": False,
        "formal": False, "admitted_prospective_pairs": 0,
        "model_improvement_proven": False, "model_promotion_allowed": False,
        "warning": "Only test-only sentinel mutations, not genuine six-boat "
                   "exhibition/120 odds; unchanged candidates diagnose the current "
                   "national-rates-only implementation, NOT a future source pipeline. "
                   "Never upgrade the frozen preregistered selector or infer success.",
    }


def read_pinned(day, ref=REF, git=None):
    if not re.fullmatch(r"20[0-9]{6}", day) or ref != REF:
        raise ValueError("unsafe_day_or_git_ref")
    def command(args):
        return subprocess.check_output(["git", *args], timeout=40)
    get = git or command
    commit = get(["rev-parse", "--verify", ref + "^{commit}"]).decode().strip()
    if not COMMIT.fullmatch(commit):
        raise ValueError("invalid_pinned_commit")
    tree = get(["ls-tree", "-r", "-z", commit, "--", "four_mode_forecasts/"])
    entries = []
    for record in tree.split(b"\0"):
        if not record:
            continue
        meta, path_raw = record.split(b"\t", 1)
        path = path_raw.decode("utf-8")
        match = RACE_FILE.fullmatch(path)
        if not match or not match.group(1).startswith(day):
            continue
        mode, kind, sha = meta.decode("ascii").split(" ")
        if mode != "100644" or kind != "blob":
            raise ValueError("nonregular_original")
        entries.append((path, sha, get(["show", commit + ":" + path])))
    return examine(entries, day, commit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="20261109")
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    result = read_pinned(a.day)
    value = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2)+"\n"
    if a.output:
        a.output.write_text(value, encoding="utf-8")
    print("FOUR_MODE_OFFICIAL_INPUT_SENSITIVITY=" +
          json.dumps(result, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
