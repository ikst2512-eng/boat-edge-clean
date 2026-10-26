"""Offline corroboration of a research forecast's first-add Git ancestry.

This verifies local Git history only. It CANNOT attest remote push/receipt time.
Use a separately authenticated remote receipt and independent reviewer.
"""
import argparse
import hashlib
import re
import subprocess
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}\Z")

def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL
    )

def verify_first_add(repo, race_code, commit_sha, trusted_ref="refs/heads/main"):
    if not re.fullmatch(r"[0-9]{12}", race_code, flags=re.ASCII):
        raise ValueError("invalid race code")
    if not HEX40.fullmatch(commit_sha):
        raise ValueError("invalid commit SHA")
    if not trusted_ref.startswith("refs/heads/"):
        raise ValueError("trusted ref must be a full branch ref")
    path = "research_snapshots/" + race_code + ".json"
    try:
        # In a shallow clone, missing ancestors can make a re-add look original.
        if git(repo, "rev-parse", "--is-shallow-repository").strip() != b"false":
            return {"verified": False, "reason": "incomplete_git_history"}
        # Git replace refs can rewrite apparent ancestry without changing SHA.
        if git(repo, "replace", "-l").strip():
            return {"verified": False, "reason": "rewritten_git_history"}
        git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir").decode().strip())
        if (git_dir / "info" / "grafts").exists():
            return {"verified": False, "reason": "rewritten_git_history"}
        git(repo, "merge-base", "--is-ancestor", commit_sha, trusted_ref)
        added = git(repo, "diff-tree", "--root", "--no-commit-id", "-r",
                    "--name-only", "--diff-filter=A", commit_sha, "--", path).decode().splitlines()
        if added != [path]:
            return {"verified": False, "reason": "not_added_in_commit"}
        # A deleted and re-added path is not the first historical introduction.
        parents = git(repo, "rev-list", "--parents", "-n", "1", commit_sha).decode().split()
        for parent in parents[1:]:
            history = git(repo, "rev-list", "-n", "1", parent, "--", path).decode().strip()
            if history:
                return {"verified": False, "reason": "path_existed_in_prior_history"}
        expected = git(repo, "show", commit_sha + ":" + path)
        current = (Path(repo) / path).read_bytes()
        if current != expected:
            return {"verified": False, "reason": "snapshot_differs_from_first_add"}
        blob = git(repo, "rev-parse", commit_sha + ":" + path).decode().strip()
    except (subprocess.CalledProcessError, OSError):
        return {"verified": False, "reason": "git_history_or_file_unavailable"}
    return {"verified": True, "first_added_commit_sha": commit_sha,
            "first_added_blob_sha": blob,
            "snapshot_sha256": hashlib.sha256(current).hexdigest(),
            "remote_receipt_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--race-code", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--trusted-ref", default="refs/heads/main")
    args = parser.parse_args()
    import json
    print(json.dumps(verify_first_add(args.repo, args.race_code,
                                     args.commit, args.trusted_ref), sort_keys=True))

if __name__ == "__main__":
    main()
