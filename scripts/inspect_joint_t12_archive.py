"""Read-only inspection of archived T12 attempt reports.

A report is NOT independent proof of the original official source. Any
successful flag remains a candidate until the original source is re-audited.
"""
import argparse
import io
import json
import zipfile
from collections import Counter
from pathlib import PurePosixPath
from urllib.request import Request, urlopen


def inspect_zip(raw, run_id):
    counts = Counter()
    seen = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) > 10000 or sum(x.file_size for x in members) > 100_000_000:
            raise ValueError("unsafe archive size")
        for member in members:
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts or member.file_size > 2_000_000:
                raise ValueError("unsafe artifact entry")
            if len(name.parts) != 2 or name.parts[0] != "reports" or not name.name.startswith("joint_") or not name.name.endswith(".json"):
                continue
            if name.name in seen:
                raise ValueError("duplicate attempt report filename")
            seen.add(name.name)
            item = json.loads(archive.read(member))
            if not isinstance(item, dict) or not isinstance(item.get("attempt"), int) or isinstance(item.get("attempt"), bool):
                raise ValueError("invalid attempt report")
            if name.name != f"joint_{item['attempt']}.json" or not 1 <= item["attempt"] <= 6:
                raise ValueError("mismatched attempt identity")
            race = item.get("race_code")
            if not isinstance(race, str) or len(race) != 12 or not race.isdecimal():
                raise ValueError("invalid race identity")
            counts["attempt_reports"] += 1
            if item.get("both_complete_before_t12") is True:
                counts["reported_complete_candidates"] += 1
    return {"run_id": run_id, "attempt_reports": counts["attempt_reports"],
            "reported_complete_candidates": counts["reported_complete_candidates"],
            "verified_source_pairs": None,
            "evidence_scope": "archived report declarations only; original sources not re-audited"}


def load_archive(repo, token, artifact_id):
    if not token or type(artifact_id) is not int or artifact_id <= 0:
        raise ValueError("missing GitHub access")
    req = Request(f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip",
                  headers={"Authorization": "Bearer " + token,
                           "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=30) as response:
        raw = response.read(100_000_001)
    if len(raw) > 100_000_000:
        raise ValueError("archive too large")
    return raw


if __name__ == "__main__":
    import os
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--run", required=True, type=int)
    p.add_argument("--artifact", required=True, type=int)
    args = p.parse_args()
    print(json.dumps(inspect_zip(load_archive(args.repo, os.environ.get("GITHUB_TOKEN"), args.artifact), args.run)))
