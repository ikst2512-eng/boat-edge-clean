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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--day-jst", default=None)
    args = p.parse_args()
    day = args.day_jst or datetime.now(JST).strftime("%Y%m%d")
    def git(*a):
        return subprocess.check_output(["git", *a], encoding="utf-8", timeout=30)
    paths = git("ls-tree", "-r", "--name-only", "HEAD", "--", "four_mode_forecasts/").splitlines()
    history = git("log", "--diff-filter=A", "--format=%H", "--name-only",
                  "HEAD", "--", "four_mode_forecasts/")
    report = audit(day, paths, parse_additions(history),
                   main_context=os.environ.get("GITHUB_REF") == "refs/heads/main")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print("FOUR_MODE_DAILY_MAIN_ARCHIVES=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
