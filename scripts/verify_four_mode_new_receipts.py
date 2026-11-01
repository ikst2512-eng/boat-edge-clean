"""Fail closed on new four-mode forecast Git receipts; no retrospective publication."""
import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATTERN = re.compile(r"^four_mode_forecasts/20[0-9]{10}\.json$")

def files_from_git(flag, ref=None):
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=A", "--", "four_mode_forecasts/"] if flag == "staged" else [
        "git", "diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r", ref, "--", "four_mode_forecasts/"
    ]
    return subprocess.check_output(cmd, text=True).splitlines()

def verify(paths, *, now=None, buffer_seconds=90):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or buffer_seconds < 0:
        raise ValueError("invalid_clock")
    for name in paths:
        if not PATTERN.fullmatch(name):
            raise ValueError("unexpected_archive_path")
        path = Path(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 30000:
            raise ValueError("invalid_archive_file")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or data.get("race_code") != path.stem:
            raise ValueError("race_identity_mismatch")
        generated = datetime.fromisoformat(data["generated_at_jst"])
        deadline = datetime.fromisoformat(data["deadline_jst"])
        if (generated.utcoffset() is None or deadline.utcoffset() is None or
            generated >= deadline - timedelta(minutes=20) or
            now >= deadline - timedelta(seconds=buffer_seconds)):
            raise ValueError("deadline_or_receipt_expired")
        if data.get("validated") is not False or data.get("target_rates_not_proven") is not True:
            raise ValueError("invalid_research_classification")
        modes = data.get("modes")
        if not isinstance(modes, dict) or set(modes) != {"hit", "balance", "hole", "narrow"}:
            raise ValueError("missing_four_modes")
        for item in modes.values():
            tickets = item.get("tickets")
            if not isinstance(tickets, list) or not tickets:
                raise ValueError("empty_mode")
            seen = set()
            for row in tickets:
                combo = row.get("combo")
                if not isinstance(combo, str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", combo):
                    raise ValueError("invalid_combo")
                if len(set(combo.split("-"))) != 3 or combo in seen:
                    raise ValueError("duplicate_or_invalid_combo")
                seen.add(combo)
    return len(paths)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--commit")
    parser.add_argument("--buffer-seconds", type=int, default=90)
    args = parser.parse_args()
    paths = files_from_git("staged" if args.staged else "commit", args.commit)
    print(json.dumps({"safe_new_archives": verify(paths, buffer_seconds=args.buffer_seconds)}))
