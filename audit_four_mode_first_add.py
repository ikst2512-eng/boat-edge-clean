"""Read-only first-add provenance audit for existing four-mode archives.

A Git committer timestamp is NOT independently verified remote first-seen.
Never promotes research forecasts to formal performance.
"""
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RACE = re.compile(r"^four_mode_forecasts/(20[0-9]{10})\.json$")
MODES = ("hit", "balance", "hole", "narrow")


def inspect(path, root=ROOT):
    rel = str(path).replace("\\", "/")
    match = RACE.fullmatch(rel)
    if not match:
        raise ValueError("invalid_path")
    history = subprocess.check_output(
        ["git", "log", "--format=%H", "--diff-filter=A", "--", rel],
        cwd=root, text=True).splitlines()
    if len(history) != 1:
        raise ValueError("first_add_not_unique")
    sha = history[0]
    first = subprocess.check_output(["git", "show", sha + ":" + rel], cwd=root)
    current = (Path(root) / rel).read_bytes()
    if first != current:
        raise ValueError("archive_changed_since_first_add")
    stamp = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", sha], cwd=root, text=True).strip()
    committed = datetime.fromisoformat(stamp)
    obj = json.loads(first)
    if (obj.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
            or obj.get("race_code") != match.group(1)
            or obj.get("status") != "provisional"
            or obj.get("validated") is not False
            or set(obj.get("modes", {})) != set(MODES)):
        raise ValueError("invalid_four_mode_archive")
    generated = datetime.fromisoformat(obj["generated_at_jst"])
    deadline = datetime.fromisoformat(obj["deadline_jst"])
    if (generated.utcoffset() != timedelta(hours=9)
            or deadline.utcoffset() != timedelta(hours=9)
            or committed.utcoffset() is None):
        raise ValueError("invalid_timezone")
    if deadline.strftime("%Y%m%d") != match.group(1)[:8]:
        raise ValueError("race_date_mismatch")
    if not (generated <= committed < deadline):
        raise ValueError("git_first_add_not_before_deadline")
    return {"race_code": match.group(1), "modes": list(MODES),
            "git_first_add_sha": sha, "git_committer_before_deadline": True,
            "archive_unchanged": True, "remote_first_seen_verified": False,
            "formal": False, "performance_eligible": False}
