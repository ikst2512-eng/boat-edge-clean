"""Read long-lived frozen third-rate prediction evidence from its Git branch.

Never recompute predictions after outcomes. The ledger only preserves what
the capture job recorded; neither Git commit dates nor branch storage prove
independent first-remote-publication or formal untouched holdout.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from four_mode_v2_frozen_third_artifact_score import score_evidence
from third_rate_evidence_ledger import BRANCH, prepare

REF = "refs/remotes/origin/" + BRANCH
PATH = re.compile(r"third_rate/(20[0-9]{6})/run-([1-9][0-9]{0,16})-attempt-([1-9][0-9]{0,16})\.json\Z")
TOPS = (1, 3, 5, 10)


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, timeout=45)


def evaluate(root, git=_git):
    root = Path(root)
    report = {
        "schema": "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1",
        "status": "no_long_lived_frozen_evidence",
        "formal": False,
        "remote_first_seen_independently_verified": False,
        "complete_capture_inventory_verified": False,
        "production_promotion_allowed": False,
        "ledger_branch": BRANCH,
        "ledger_files": 0, "frozen": 0, "paired": 0,
        "pending_results": 0, "invalid": 0, "excluded": 0,
        "invalid_files": [], "race_codes_paired": [],
        "paired_race_scores": [],
        "race_codes_frozen": [], "frozen_ticket_hashes": {},
        "by_race_day_jst": {},
        "topn": {f"top{n}": {"baseline": 0, "candidate": 0,
                           "gained": 0, "lost": 0} for n in TOPS},
        "warning": "Git branch preserves original same-job shadow bytes, not independent source receipt or full capture-run completeness.",
    }
    try:
        names = git(root, "ls-tree", "-r", "--name-only",
                    REF, "--", "third_rate/").decode("utf-8").splitlines()
    except (OSError, UnicodeError, subprocess.SubprocessError):
        report["status"] = "ledger_branch_unavailable"
        return report
    if not names:
        return report
    report["ledger_files"] = len(names)
    seen = set()
    for path in sorted(names):
        match = PATH.fullmatch(path)
        if not match:
            report["invalid_files"].append(path[:180])
            continue
        day, run_id, attempt = match.groups()
        try:
            original = git(root, "show", REF + ":" + path)
            if prepare(original, root, run_id, attempt) != path:
                raise ValueError("ledger_source_path_mismatch")
            evidence = json.loads(original)
            scoring = score_evidence(evidence, root)
            if scoring["invalid"] or scoring.get("validation_error_count", 0):
                report["invalid_files"].append(path)
            frozen_codes = scoring["race_codes_frozen"]
            # Validate the entire entry before changing the accepted roster.
            # If a later row overlaps a prior ledger entry, none of this
            # rejected file's otherwise-new races may poison later siblings.
            if (len(frozen_codes) != len(set(frozen_codes))
                    or not seen.isdisjoint(frozen_codes)):
                raise ValueError("repeated_frozen_race")
            seen.update(frozen_codes)
            for field in ("frozen", "paired", "pending_results", "invalid", "excluded"):
                report[field] += scoring[field]
            report["race_codes_paired"].extend(scoring["race_codes_paired"])
            report["paired_race_scores"].extend(scoring["paired_race_scores"])
            report["race_codes_frozen"].extend(scoring["race_codes_frozen"])
            report["frozen_ticket_hashes"].update(scoring["frozen_ticket_hashes"])
            for n in TOPS:
                for field in ("baseline", "candidate", "gained", "lost"):
                    report["topn"][f"top{n}"][field] += scoring["topn"][f"top{n}"][field]
            for race in scoring["paired_race_scores"]:
                code = race["race_code"]
                bucket = report["by_race_day_jst"].setdefault(code[:8], {
                    "paired": 0, "race_codes": [],
                    "topn": {f"top{n}": {"baseline": 0, "candidate": 0,
                                        "gained": 0, "lost": 0} for n in TOPS},
                })
                bucket["paired"] += 1
                bucket["race_codes"].append(code)
                for n in TOPS:
                    for field in ("baseline", "candidate", "gained", "lost"):
                        bucket["topn"][f"top{n}"][field] += race["topn"][f"top{n}"][field]
        except (ValueError, TypeError, KeyError, OSError, UnicodeError,
                subprocess.SubprocessError, json.JSONDecodeError):
            report["invalid_files"].append(path)
    report["by_race_day_jst"] = dict(sorted(report["by_race_day_jst"].items()))
    for day in report["by_race_day_jst"].values():
        day["race_codes"].sort()
    report["race_codes_paired"].sort()
    report["paired_race_scores"].sort(key=lambda row: row["race_code"])
    report["race_codes_frozen"].sort()
    if len(set(report["race_codes_frozen"])) != report["frozen"]:
        report["invalid_files"].append("duplicate_frozen_roster")
    if (len(report["paired_race_scores"]) != report["paired"]
            or [row["race_code"] for row in report["paired_race_scores"]]
            != report["race_codes_paired"]):
        raise ValueError("ledger_per_race_score_partition_mismatch")
    if (len(report["race_codes_paired"]) != report["paired"]
            or len(set(report["race_codes_paired"])) != report["paired"]
            or sum(d["paired"] for d in report["by_race_day_jst"].values()) != report["paired"]
            or sorted(code for d in report["by_race_day_jst"].values()
                      for code in d["race_codes"]) != report["race_codes_paired"]):
        raise ValueError("ledger_paired_race_partition_mismatch")
    for n in TOPS:
        for field in ("baseline", "candidate", "gained", "lost"):
            if sum(d["topn"][f"top{n}"][field] for d in report["by_race_day_jst"].values()) != report["topn"][f"top{n}"][field]:
                raise ValueError("ledger_daily_score_mismatch")
    report["status"] = ("incomplete_or_invalid_ledger_evidence" if report["invalid_files"]
                        else "durable_frozen_evidence_scored")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    summary = evaluate(args.root)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("V2_THIRD_RATE_DURABLE_LEDGER=" + json.dumps(summary, sort_keys=True))
    if summary["status"] in ("incomplete_or_invalid_ledger_evidence",
                             "ledger_branch_unavailable"):
        raise SystemExit(2)
