"""Guard CLEAN Git first-add chronology at Git's whole-second precision.

Read-only with respect to immutable JSON. A delayed *real* commit (never a
faked Git date) must be strictly later than the candidates' generated_at.
Neither a successful local gate nor Git metadata proves remote first-seen.
"""
import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
PATH = re.compile(r"prospective_predictions/(20[0-9]{10})\.json")


def candidate_paths(stage, root=Path(".")):
    command = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=A", "--", "prospective_predictions/"]
        if stage == "precommit" else
        ["git", "diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r",
         "HEAD", "--", "prospective_predictions/"]
    )
    paths = subprocess.check_output(command, cwd=root, text=True).splitlines()
    if not paths or any(PATH.fullmatch(path) is None for path in paths):
        raise ValueError("CLEAN staged/committed first-add paths missing or invalid")
    return paths


def load_records(paths, root=Path("."), source="worktree"):
    """Read the exact staged/committed immutable bytes when verifying Git."""
    records = []
    for path in paths:
        if source == "staged":
            raw = subprocess.check_output(["git", "show", f":{path}"], cwd=root)
        elif source == "committed":
            raw = subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=root)
        elif source == "worktree":
            raw = (root / path).read_bytes()
        else:
            raise ValueError("unknown CLEAN record source")
        record = json.loads(raw)
        code = PATH.fullmatch(path).group(1)
        if record.get("race_code") != code:
            raise ValueError("CLEAN first-add race identity mismatch")
        generated = datetime.fromisoformat(record["generated_at"])
        cutoff = datetime.fromisoformat(record["cutoff_jst"])
        if (generated.utcoffset() != timedelta(hours=9)
                or cutoff.utcoffset() != timedelta(hours=9)
                or generated >= cutoff):
            raise ValueError("CLEAN first-add timestamp invalid")
        records.append((code, generated, cutoff))
    return records


def after_generation_second(records):
    """First instant with a whole-second Git timestamp strictly after output."""
    return max(generated.replace(microsecond=0) + timedelta(seconds=1)
               for _, generated, _ in records)


def ensure_safe_commit_time(records, commit_at):
    if commit_at.tzinfo is None:
        raise ValueError("CLEAN Git committer timestamp untrusted")
    if any(commit_at <= generated for _, generated, _ in records):
        raise ValueError("CLEAN Git committer not strictly after generation")
    if any(commit_at >= cutoff for _, _, cutoff in records):
        raise ValueError("CLEAN Git committer not before T-12")
    return True


def prepare(records, clock=None, pause=None):
    """Wait at most two seconds for a real later clock tick, then recheck T-12."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    pause = pause or time.sleep
    now = clock()
    if now.tzinfo is None:
        raise ValueError("CLEAN system clock untrusted")
    wait = (after_generation_second(records) - now).total_seconds()
    if wait > 2:
        raise ValueError("CLEAN generation/runner clock skew unverified")
    if wait > 0:
        pause(wait + 0.04)
    observed = clock()
    if observed.tzinfo is None or observed < after_generation_second(records):
        raise ValueError("CLEAN Git committer second not yet observable")
    if any(observed >= cutoff - timedelta(seconds=90) for _, _, cutoff in records):
        raise ValueError("CLEAN first-add 90-second receipt buffer expired")
    return observed


def run(stage, root=Path(".")):
    paths = candidate_paths(stage, root)
    records = load_records(paths, root, source=(
        "staged" if stage == "precommit" else "committed"))
    if stage == "precommit":
        when = prepare(records)
    elif stage == "postcommit":
        raw = subprocess.check_output(
            ["git", "show", "-s", "--format=%cI", "HEAD"],
            cwd=root, text=True).strip()
        when = datetime.fromisoformat(raw)
        ensure_safe_commit_time(records, when)
    else:
        raise ValueError("unknown CLEAN clock gate stage")
    print("CLEAN_COMMIT_CLOCK_GATE " + json.dumps({
        "stage": stage, "candidate_count": len(records),
        "checked_at": when.isoformat(),
        "local_timestamp_order_passed": True,
        "remote_first_seen_verified": False, "formal": False,
    }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("precommit", "postcommit"))
    run(parser.parse_args().stage)
