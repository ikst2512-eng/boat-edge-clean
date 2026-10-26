"""Read-only consistency gate for GitHub Actions artifact metadata.

The caller must fetch run/artifact information from GitHub independently.
This never certifies formal model provenance or grants public availability.
"""
from datetime import datetime
from formal_candidate_validator import InvalidCandidate, _timestamp


def inspect_actions_artifact(candidate, receipt, run, artifact):
    if not all(isinstance(x, dict) for x in (candidate, receipt, run, artifact)):
        raise InvalidCandidate("missing independent metadata")
    run_id = receipt.get("workflow_run_id")
    attempt = receipt.get("workflow_attempt")
    if type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt <= 0:
        raise InvalidCandidate("receipt run identity invalid")
    if type(run.get("id")) is not int or type(run.get("run_attempt")) is not int or run["id"] != run_id or run["run_attempt"] != attempt:
        raise InvalidCandidate("run identity mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise InvalidCandidate("capture run not successful")
    if run.get("event") != "repository_dispatch":
        raise InvalidCandidate("unexpected capture trigger")
    workflow_ref = artifact.get("workflow_run")
    if not isinstance(workflow_ref, dict) or type(workflow_ref.get("id")) is not int or workflow_ref["id"] != run_id:
        raise InvalidCandidate("artifact does not belong to run")
    if artifact.get("expired") is not False or type(artifact.get("size_in_bytes")) is not int or artifact["size_in_bytes"] <= 0:
        raise InvalidCandidate("artifact absent or expired")
    if artifact.get("name") != f"prospective-v5-{run_id}":
        raise InvalidCandidate("unexpected artifact")
    deadline = _timestamp(candidate.get("deadline_at"))
    frozen = _timestamp(candidate.get("generated_at"))
    # GitHub's publication metadata is useful only as a *necessary* condition.
    cutoff = deadline.timestamp() - 12 * 60
    created = _timestamp(artifact.get("created_at"))
    if not frozen.timestamp() <= created.timestamp() < cutoff:
        raise InvalidCandidate("artifact uploaded after cutoff or before generation")
    return {"github_artifact_metadata_consistent": True,
            "downloaded_bytes_verified": False, "model_authenticity_verified": False,
            "formal_approved": False}
