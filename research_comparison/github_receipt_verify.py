"""Read-only GitHub server receipt verification for research forecasts.

Fetch commit/path through GitHub's API and match an Actions push run to that
commit. Never fetch results or assert model quality. API created_at provides
server observation, not source authenticity or formal Fresh eligibility.
"""
import base64
import hashlib
import json
import re
from datetime import datetime, timedelta

HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")

def dt(value):
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timezone required")
    return timestamp

def verify(fetch_json, *, repo, branch, commit, path, expected_sha256,
           official_deadline, run_id):
    """fetch_json(relative API path) -> decoded dict, from trusted GitHub API."""
    if repo != "ikst2512-eng/boat-edge-clean":
        raise ValueError("unapproved repository")
    if not HEX40.fullmatch(commit) or not HEX64.fullmatch(expected_sha256):
        raise ValueError("invalid SHA")
    if not re.fullmatch(r"research_prospective_pairs/[0-9]{12}\.json", path):
        raise ValueError("unapproved pair path")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("invalid run ID")
    cutoff = dt(official_deadline) - timedelta(minutes=12)
    prefix = "/repos/" + repo
    run = fetch_json(prefix + "/actions/runs/" + str(run_id))
    if (run.get("event") != "push" or run.get("head_sha") != commit
        or run.get("head_branch") != branch
        or run.get("repository", {}).get("full_name") != repo
        or run.get("status") != "completed"
        or dt(run["created_at"]) >= cutoff):
        raise ValueError("server run not an eligible pre-cutoff push")
    info = fetch_json(prefix + "/git/commits/" + commit)
    tree_sha = info["tree"]["sha"]
    if not HEX40.fullmatch(tree_sha):
        raise ValueError("invalid tree SHA")
    tree = fetch_json(prefix + "/git/trees/" + tree_sha + "?recursive=1")
    if tree.get("truncated"):
        raise ValueError("truncated tree")
    found = [x for x in tree.get("tree", []) if x.get("path") == path]
    if len(found) != 1 or found[0].get("type") != "blob":
        raise ValueError("path missing from commit tree")
    blob_sha = found[0].get("sha")
    if not isinstance(blob_sha, str) or not HEX40.fullmatch(blob_sha):
        raise ValueError("invalid blob SHA")
    blob = fetch_json(prefix + "/git/blobs/" + blob_sha)
    if blob.get("encoding") != "base64":
        raise ValueError("unsupported blob encoding")
    raw = base64.b64decode(blob["content"], validate=False)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("committed bytes digest mismatch")
    if ("blob " + str(len(raw)) + "\0").encode() == b"":
        raise AssertionError("unreachable")
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if git_blob != blob_sha:
        raise ValueError("blob does not match Git object SHA")
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("expected JSON record")
    expected_code = path.rsplit("/", 1)[1][:-5]
    if record.get("race_code") != expected_code:
        raise ValueError("race code/path mismatch")
    if dt(record["cutoff_jst"]) != cutoff:
        raise ValueError("record cutoff differs from official cutoff")
    return {"status": "SERVER_PUSH_AND_COMMIT_BLOB_MATCH",
            "run_id": run_id, "run_created_at": run["created_at"],
            "commit_sha": commit, "blob_sha": blob_sha,
            "sha256": expected_sha256, "path": path,
            "formal_validated": False, "outcome_access_authorized": False,
            "limitations": "Does not verify source authenticity, prediction model, first addition or preregistration."}
