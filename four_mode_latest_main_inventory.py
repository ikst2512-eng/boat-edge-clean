"""Read-only inventory of the *latest fetched main tree* for the future 4-mode study.

A Git tree entry only proves that the named blob exists in that snapshot.
It proves neither pre-T-12 publication nor any independent result or
unbroken run inventory. NEVER call this an eligible or formal denominator.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIRST_DAY = "20261105"
LAST_DAY = "20261231"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RACE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
PATHS = {
    "four_mode_forecasts": "four_mode",
    "prospective_predictions": "clean_separate_collector",
    "confirmed_results": "confirmed_result_file",
}
OMIT = {"four_mode_forecasts/capture_status.json"}


def inspect_main_tree(root=ROOT, git=None):
    """Require an explicitly fetched origin/main, never silently use PR HEAD."""
    root = Path(root)
    git = git or (lambda args: subprocess.check_output(["git", *args], cwd=root, timeout=30))
    commit = git(["rev-parse", "--verify", "refs/remotes/origin/main"])
    if type(commit) is not bytes:
        raise ValueError("untrusted_main_ref")
    sha = commit.decode("ascii").strip()
    if SHA.fullmatch(sha) is None:
        raise ValueError("untrusted_main_ref")
    tree = git(["ls-tree", "-r", "-z", sha, "--", *PATHS])
    if type(tree) is not bytes or len(tree) > 15_000_000:
        raise ValueError("untrusted_main_tree")
    found = {name: set() for name in PATHS.values()}
    seen = set()
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        try:
            meta, name = entry.split(b"\t", 1)
            mode, kind, blob = meta.decode("ascii").split(" ")
            path = name.decode("ascii")
        except (ValueError, UnicodeError) as exc:
            raise ValueError("untrusted_main_tree_row") from exc
        if (mode != "100644" or kind != "blob"
                or SHA.fullmatch(blob) is None
                or path in seen or path.startswith("/")
                or ".." in path.split("/")):
            raise ValueError("invalid_or_duplicate_main_tree_path")
        seen.add(path)
        if path in OMIT:
            continue
        folder, sep, tail = path.partition("/")
        if (not sep or folder not in PATHS or "/" in tail
                or not tail.endswith(".json")
                or RACE.fullmatch(tail[:-5]) is None):
            # A non-race file under these evidence paths must not look like
            # a valid race or enter a scored denominator.
            continue
        code = tail[:-5]
        if FIRST_DAY <= code[:8] <= LAST_DAY:
            found[PATHS[folder]].add(code)
    four = found["four_mode"]
    clean = found["clean_separate_collector"]
    results = found["confirmed_result_file"]
    by_day = {}
    for day in sorted({code[:8] for records in found.values() for code in records}):
        by_day[day] = {
            "four_mode_file_count": sum(code.startswith(day) for code in four),
            "clean_separate_file_count": sum(code.startswith(day) for code in clean),
            "confirmed_result_file_count": sum(code.startswith(day) for code in results),
            "four_mode_with_result_filename": sum(
                code.startswith(day) and code in results for code in four),
        }
    return {
        "schema": "FOUR_MODE_LATEST_MAIN_TREE_INVENTORY_V1",
        "status": ("unverified_four_mode_main_files_present" if four
                   else "no_four_mode_files_in_examined_main_tree"),
        "main_tree_sha": sha,
        "race_window_jst": {"first": FIRST_DAY, "last": LAST_DAY},
        "four_mode_file_count": len(four),
        "four_mode_codes": sorted(four),
        "clean_separate_file_count": len(clean),
        "clean_separate_codes": sorted(clean),
        "confirmed_result_file_count": len(results),
        "four_mode_with_result_filename": len(four & results),
        "four_mode_without_result_filename": len(four - results),
        "by_day": by_day,
        "main_inventory_exhaustive_at_commit": True,
        "capture_run_inventory_exhaustive": False,
        "first_git_add_checked": False,
        "github_server_observation_checked": False,
        "source_beforeinfo_and_six_boats_verified": False,
        "result_content_independently_verified": False,
        "research_eligible_race_count": None,
        "formal_eligible_race_count": None,
        "formal": False,
        "model_improvement_proven": False,
        "warning": ("Only file names in a specific fetched main Git tree; "
                    "not a capture-run or chronology audit. Missing filenames "
                    "are not failed predictions; result filenames are not "
                    "independently confirmed finishes. A PR-branch checkout "
                    "must fetch main before using this command.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="four_mode_latest_main_inventory.json")
    args = parser.parse_args()
    report = inspect_main_tree()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                            sort_keys=True) + "\n", encoding="utf-8")
    print("FOUR_MODE_MAIN_TREE_INVENTORY=" + json.dumps({
        key: report[key] for key in (
            "status", "main_tree_sha", "four_mode_file_count",
            "clean_separate_file_count", "confirmed_result_file_count",
            "four_mode_with_result_filename", "by_day",
            "research_eligible_race_count", "formal_eligible_race_count")
    }, sort_keys=True))


if __name__ == "__main__":
    main()
