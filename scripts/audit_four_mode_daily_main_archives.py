"""Read-only daily V2 main-tree and first-add existence audit.

Git history only proves an archive exists in this checkout's ancestry.
It NEVER proves a predeadline source receipt, external first-seen timestamp,
accurate prediction, or independent remote publication.
"""
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
ARCHIVE = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def parse_additions(raw):
    if not isinstance(raw, str):
        raise ValueError("invalid history")
    current = None
    entries = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if SHA.fullmatch(line):
            current = line
            continue
        if line == "four_mode_forecasts/capture_status.json":
            continue
        if line.startswith("four_mode_forecasts/"):
            if current is None or not ARCHIVE.fullmatch(line):
                raise ValueError("invalid archive addition in history")
            entries.setdefault(line, []).append(current)
    return entries


def audit(day, paths, additions, *, main_context):
    if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid JST date")
    if not isinstance(paths, list) or not isinstance(additions, dict):
        raise ValueError("invalid Git inventory")
    archives = set()
    for path in paths:
        if not isinstance(path, str) or not path.startswith("four_mode_forecasts/"):
            raise ValueError("unexpected Git path")
        if ARCHIVE.fullmatch(path):
            if path in archives:
                raise ValueError("duplicate tree path")
            archives.add(path)
    today = sorted(p for p in archives if Path(p).name.startswith(day))
    matching = []
    missing = []
    multiple = []
    for path in today:
        first_adds = additions.get(path, [])
        if not isinstance(first_adds, list):
            raise ValueError("malformed history entries")
        if len(first_adds) == 1 and isinstance(first_adds[0], str) and SHA.fullmatch(first_adds[0]):
            matching.append(path)
        elif len(first_adds) > 1:
            multiple.append(path)
        else:
            missing.append(path)
    has_archive = bool(today)
    complete = has_archive and not (missing or multiple)
    return {
        "schema": "FOUR_MODE_DAILY_MAIN_ARCHIVES_V1",
        "day_jst": day,
        "checkout_main_context": bool(main_context),
        "total_forecast_archives_in_checkout": len(archives),
        "today_archive_count": len(today),
        "today_single_first_add_count": len(matching),
        "today_missing_first_add_count": len(missing),
        "today_multiple_first_add_count": len(multiple),
        "today_first_add_commit_shas": sorted({additions[p][0] for p in matching}),
        "assessment": (
            "not_main_checkout" if not main_context else
            "no_new_day_archives_yet" if not has_archive else
            "git_first_add_incomplete" if not complete else
            "new_day_git_archives_found"
        ),
        "main_git_addition_evidence_present": bool(main_context and complete),
        "independent_remote_first_seen_verified": False,
        "source_predeadline_verified": False,
        "note": "Git addition evidence is not external receipt or first-seen proof.",
    }




def inspect_first_add_commit_days(day, additions, paths, stamp_for_sha):
    """Report same-JST-day Git commit timestamps, not remote first-seen times."""
    counts = {"same_day": 0, "other_day": 0, "unknown": 0}
    other_day_paths = []
    commit_days = {}
    for name in paths:
        if not ARCHIVE.fullmatch(name) or not Path(name).name.startswith(day):
            continue
        shas = additions.get(name, [])
        if len(shas) != 1 or not isinstance(shas[0], str) or not SHA.fullmatch(shas[0]):
            counts["unknown"] += 1
            continue
        sha = shas[0]
        if sha not in commit_days:
            try:
                raw = stamp_for_sha(sha)
                instant = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
                if instant.tzinfo is None:
                    raise ValueError("timezone absent")
                commit_days[sha] = instant.astimezone(JST).strftime("%Y%m%d")
            except (OSError, UnicodeError, ValueError, TypeError, subprocess.SubprocessError):
                commit_days[sha] = None
        if commit_days[sha] is None:
            counts["unknown"] += 1
        elif commit_days[sha] == day:
            counts["same_day"] += 1
        else:
            counts["other_day"] += 1
            other_day_paths.append(name)
    return counts, other_day_paths


def inspect_day_archive_versions(day, paths, root=Path(".")):
    """Inspect checked-out archive payloads; this does not prove remote timing."""
    counts = {"v2": 0, "other_model": 0, "invalid": 0}
    invalid_paths = []
    for name in paths:
        if not ARCHIVE.fullmatch(name) or not Path(name).name.startswith(day):
            continue
        try:
            path = root / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
                raise ValueError("invalid archive file")
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or not isinstance(record.get("model_version"), str):
                raise ValueError("missing model version")
            if record["model_version"].startswith("CLEAN_FOUR_MODES_V2_"):
                counts["v2"] += 1
            else:
                counts["other_model"] += 1
        except (OSError, UnicodeError, ValueError):
            counts["invalid"] += 1
            invalid_paths.append(name)
    return counts, invalid_paths


def positive_eligible_run_ids(day, evidence_reports):
    """Use same-day newly generated/staged candidate evidence, never local archive totals."""
    confirmed = set()
    for report in evidence_reports:
        if not isinstance(report, dict) or not isinstance(report.get("runs"), list):
            continue
        for row in report["runs"]:
            if not isinstance(row, dict) or row.get("artifact_present") is not True:
                continue
            # generated_today is just len(local saved archive files),
            # not evidence of newly generated candidates. In particular,
            # it may be zero when a new archive failed to reach main.
            # Require a positive per-execution candidate or staging count.
            generated = row.get("newly_generated")
            staged = row.get("staged_valid")
            added = row.get("claimed_added_forecasts")
            if not any(type(value) is int and value > 0
                       for value in (generated, staged, added)):
                continue
            try:
                stamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    continue
                day_of_run = stamp.astimezone(JST).strftime("%Y%m%d")
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            if day_of_run == day and type(row.get("run_id")) is int:
                confirmed.add(row["run_id"])
    return sorted(confirmed)



def reconcile_claimed_pushes(day, paths, additions, evidence_reports):
    """Cross-check artifact push claims against same-day first-add Git history.

    A local artifact is only a claim. A matching Git first-add SHA and count
    establish archive correspondence in the checkout, not remote first-seen.
    """
    valid_paths = set(paths)
    by_sha = {}
    for path in valid_paths:
        if ARCHIVE.fullmatch(path) and Path(path).name.startswith(day):
            shas = additions.get(path, [])
            if len(shas) == 1 and isinstance(shas[0], str) and SHA.fullmatch(shas[0]):
                by_sha[shas[0]] = by_sha.get(shas[0], 0) + 1
    checked = []
    mismatched = []
    seen = set()
    for report in evidence_reports:
        if not isinstance(report, dict) or not isinstance(report.get("runs"), list):
            continue
        for row in report["runs"]:
            if not isinstance(row, dict) or row.get("artifact_present") is not True:
                continue
            if row.get("publication_outcome") != "pushed_to_main":
                continue
            try:
                stamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if stamp.tzinfo is None or stamp.astimezone(JST).strftime("%Y%m%d") != day:
                    continue
            except (KeyError, AttributeError, ValueError, TypeError):
                continue
            run_id = row.get("run_id")
            if type(run_id) is not int or run_id <= 0 or run_id in seen:
                continue
            seen.add(run_id)
            sha = row.get("claimed_commit_sha")
            claimed = row.get("claimed_added_forecasts")
            actual = by_sha.get(sha, 0) if isinstance(sha, str) and SHA.fullmatch(sha) else 0
            match = bool(isinstance(sha, str) and SHA.fullmatch(sha)
                         and type(claimed) is int and claimed > 0 and actual == claimed)
            record = {"run_id": run_id, "claimed_commit_sha": sha,
                      "claimed_added_forecasts": claimed, "first_add_archives_in_checkout": actual}
            if match:
                checked.append(record)
            else:
                mismatched.append(record)
    return checked, mismatched


def reconcile_research_rosters_with_main(day, paths, additions, evidence_reports):
    """Compare locally self-consistent research IDs with Git first-add paths.

    A local shadow roster matching the local push claim is not independently
    proof of the actual Git addition roster. Verify that extra identity here.
    Missing old shadow artifacts remain UNKNOWN, not a failure or a success.
    """
    valid_paths = set(paths)
    by_sha = {}
    for path in valid_paths:
        if ARCHIVE.fullmatch(path) and Path(path).name.startswith(day):
            shas = additions.get(path, [])
            if len(shas) == 1 and isinstance(shas[0], str) and SHA.fullmatch(shas[0]):
                by_sha.setdefault(shas[0], set()).add(Path(path).stem)
    matched, mismatched, unknown = [], [], []
    seen = set()
    for evidence in evidence_reports:
        if not isinstance(evidence, dict) or not isinstance(evidence.get("runs"), list):
            continue
        for row in evidence["runs"]:
            if not isinstance(row, dict) or row.get("publication_outcome") != "pushed_to_main":
                continue
            try:
                stamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if stamp.tzinfo is None or stamp.astimezone(JST).strftime("%Y%m%d") != day:
                    continue
            except (KeyError, AttributeError, TypeError, ValueError):
                continue
            run_id = row.get("run_id")
            if type(run_id) is not int or run_id <= 0 or run_id in seen:
                continue
            seen.add(run_id)
            roster = row.get("research_roster_evidence")
            # An explicit contradiction from both preserved same-job research
            # artifacts is not merely missing evidence. Escalate it in the
            # scheduled main audit, while legacy/missing records stay unknown.
            if isinstance(roster, dict) and roster.get("status") == "mismatch":
                mismatched.append({
                    "run_id": run_id,
                    "reason": "research_artifacts_disagree",
                    "artifact_reason": roster.get("reason"),
                })
                continue
            if not isinstance(roster, dict) or roster.get("status") != "matched":
                unknown.append(run_id)
                continue
            sha = row.get("claimed_commit_sha")
            codes = roster.get("race_codes")
            if (not isinstance(sha, str) or not SHA.fullmatch(sha)
                    or roster.get("commit_sha") != sha
                    or not isinstance(codes, list) or not codes
                    or any(not isinstance(code, str) or
                           not re.fullmatch(r"20[0-9]{10}", code)
                           for code in codes)
                    or len(codes) != len(set(codes))
                    or len(codes) != row.get("claimed_added_forecasts")):
                mismatched.append({"run_id": run_id, "reason": "invalid_research_roster_identity"})
                continue
            actual = by_sha.get(sha, set())
            if set(codes) == actual:
                matched.append({"run_id": run_id, "matched_races": len(codes),
                                "git_first_add_commit_sha": sha})
            else:
                mismatched.append({"run_id": run_id, "reason": "research_vs_git_first_add_roster",
                                   "research_count": len(codes), "git_count": len(actual),
                                   "research_only": sorted(set(codes) - actual)[:10],
                                   "git_only": sorted(actual - set(codes))[:10]})
    return matched, mismatched, unknown


def ledger_failure_run_ids(day, evidence_reports):
    """Only explicit failures on the current JST day; missing is unknown."""
    bad = set()
    for report in evidence_reports:
        if not isinstance(report, dict) or not isinstance(report.get("runs"), list):
            continue
        for row in report["runs"]:
            if not isinstance(row, dict):
                continue
            try:
                stamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if stamp.tzinfo is None or stamp.astimezone(JST).strftime("%Y%m%d") != day:
                    continue
            except (KeyError, AttributeError, ValueError, TypeError):
                continue
            run_id = row.get("run_id")
            if (type(run_id) is int and run_id > 0
                    and (row.get("third_rate_ledger_outcome") == "failure"
                         or row.get("third_rate_ledger_status") == "ledger_preservation_failed")):
                bad.add(run_id)
    return sorted(bad)


def github_observation_failure_run_ids(day, evidence_reports):
    """Explicit same-JST-day server observation or ledger failures only."""
    failures = set()
    for report in evidence_reports:
        if not isinstance(report, dict) or not isinstance(report.get("runs"), list):
            continue
        for row in report["runs"]:
            if not isinstance(row, dict):
                continue
            try:
                stamp = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if stamp.tzinfo is None or stamp.astimezone(JST).strftime("%Y%m%d") != day:
                    continue
            except (KeyError, AttributeError, ValueError, TypeError):
                continue
            run_id = row.get("run_id")
            if (type(run_id) is int and run_id > 0 and (
                    row.get("github_server_observation_outcome") == "failure"
                    or row.get("github_observation_ledger_outcome") == "failure"
                    or row.get("github_observation_ledger_status") == "observation_preservation_failed")):
                failures.add(run_id)
    return sorted(failures)


def scheduled_audit_alert(result, event, evidence_reports=()):
    if event != "schedule" or result.get("checkout_main_context") is not True:
        return False
    if result.get("assessment") == "git_first_add_incomplete":
        return True
    if result.get("assessment") == "no_new_day_archives_yet":
        return bool(positive_eligible_run_ids(result["day_jst"], evidence_reports))
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--day-jst", default=None)
    p.add_argument("--capture-evidence", nargs="*", default=[])
    args = p.parse_args()
    day = args.day_jst or datetime.now(JST).strftime("%Y%m%d")
    def git(*a):
        return subprocess.check_output(["git", *a], encoding="utf-8", timeout=30)
    paths = git("ls-tree", "-r", "--name-only", "HEAD", "--", "four_mode_forecasts/").splitlines()
    history = git("log", "--diff-filter=A", "--format=%H", "--name-only",
                  "HEAD", "--", "four_mode_forecasts/")
    additions = parse_additions(history)
    report = audit(day, paths, additions,
                   main_context=os.environ.get("GITHUB_REF") == "refs/heads/main")
    commit_days, other_day_paths = inspect_first_add_commit_days(
        day, additions, paths, lambda sha: git("show", "-s", "--format=%cI", sha))
    report["today_first_add_commit_same_jst_day_count"] = commit_days["same_day"]
    report["today_first_add_commit_other_jst_day_count"] = commit_days["other_day"]
    report["today_first_add_commit_day_unknown_count"] = commit_days["unknown"]
    report["today_first_add_commit_other_day_paths"] = other_day_paths[:20]
    report["same_day_git_commit_time_verified"] = (
        report["today_archive_count"] > 0
        and commit_days["same_day"] == report["today_archive_count"])
    versions, invalid_paths = inspect_day_archive_versions(day, paths)
    report["today_v2_archive_count"] = versions["v2"]
    report["today_other_model_archive_count"] = versions["other_model"]
    report["today_invalid_archive_count"] = versions["invalid"]
    report["today_invalid_archive_paths"] = invalid_paths[:20]
    report["v2_archive_payloads_verified"] = (
        report["today_archive_count"] > 0
        and versions["v2"] == report["today_archive_count"]
        and versions["invalid"] == 0
    )
    # Version assertions are about checkout contents only, not independent
    # receipt timestamps or source acquisition.
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    for source in args.capture_evidence:
        try:
            evidence.append(json.loads(Path(source).read_text(encoding="utf-8")))
        except (OSError, UnicodeError, ValueError):
            evidence.append(None)
    eligible_ids = positive_eligible_run_ids(day, evidence)
    report["matching_day_eligible_capture_run_ids"] = eligible_ids
    report["third_rate_ledger_failure_run_ids"] = ledger_failure_run_ids(day, evidence)
    report["github_observation_failure_run_ids"] = github_observation_failure_run_ids(day, evidence)
    verified_claims, mismatched_claims = reconcile_claimed_pushes(
        day, paths, additions, evidence)
    report["claimed_push_first_add_verified_runs"] = verified_claims
    report["claimed_push_first_add_mismatched_runs"] = mismatched_claims
    report["claimed_push_archive_reconciliation_verified"] = bool(verified_claims) and not mismatched_claims
    matching_rosters, mismatched_rosters, unknown_rosters = (
        reconcile_research_rosters_with_main(day, paths, additions, evidence))
    report["research_git_roster_verified_runs"] = matching_rosters
    report["research_git_roster_mismatched_runs"] = mismatched_rosters
    report["research_git_roster_unknown_run_ids"] = unknown_rosters
    report["research_git_roster_reconciliation_verified"] = (
        bool(matching_rosters) and not mismatched_rosters)
    report["daily_alert_basis"] = (
        "incomplete_git_first_add" if report["assessment"] == "git_first_add_incomplete" else
        "new_candidates_without_main_archives" if report["assessment"] == "no_new_day_archives_yet" and eligible_ids else
        "unverified_or_no_eligible_capture" if report["assessment"] == "no_new_day_archives_yet" else
        "archives_present_or_pr_checkout")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("FOUR_MODE_DAILY_MAIN_ARCHIVES=" + json.dumps(report, sort_keys=True))
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and report["github_observation_failure_run_ids"]):
        print("::error::GitHub server observation or append-only evidence preservation explicitly failed")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and report["third_rate_ledger_failure_run_ids"]):
        print("::error::Durable third-rate ledger explicitly failed in inspected capture evidence")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and mismatched_rosters):
        print("::error::V2 research race roster does not match Git main first-add identities")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and mismatched_claims):
        print("::error::Claimed V2 publication commit or archive count absent from checked-out Git main")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and report["today_archive_count"] > 0
            and not report["same_day_git_commit_time_verified"]):
        print("::error::Daily V2 archive first-add Git commit dates are mismatched or unknown")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and report["today_archive_count"] > 0
            and not report["v2_archive_payloads_verified"]):
        print("::error::Today's saved research archives are not all readable V2 payloads")
        raise SystemExit(2)
    if scheduled_audit_alert(report, os.environ.get("GITHUB_EVENT_NAME"), evidence):
        print("::error::Daily V2 main archives missing despite new local candidate or staged evidence, or Git first-add history incomplete")
        raise SystemExit(2)
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and report["assessment"] == "no_new_day_archives_yet"):
        print("::warning::Daily V2 archives absent; positive new-candidate or staged evidence is unverified")


if __name__ == "__main__":
    main()
