"""Read-only download of a specified CLEAN candidate artifact for offline audit.

This never creates formal forecasts, fetches results, or approves any candidate.
Requires an independently supplied candidate digest and explicit Actions IDs.
"""
import argparse
import json
import os
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from formal_candidate_validator import InvalidCandidate
from formal_artifact_zip_inspector import inspect_downloaded_artifact
from formal_actions_artifact_audit import inspect_actions_artifact

API = "https://api.github.com/repos/ikst2512-eng/boat-edge-clean"
ALLOWED_REDIRECT_HOSTS = ("objects.githubusercontent.com", "pipelines.actions.githubusercontent.com",
                          "results-receiver.actions.githubusercontent.com")


class NoAuthCrossHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != "https" or target.hostname not in ALLOWED_REDIRECT_HOSTS:
            raise InvalidCandidate("untrusted artifact redirect host")
        return Request(newurl, headers={"User-Agent": "boat-edge-clean-formal-audit/1.0"})


def _strict_metadata_json(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InvalidCandidate("duplicate GitHub metadata key")
            result[key] = value
        return result
    def reject_nonfinite(value):
        raise InvalidCandidate("nonfinite GitHub metadata")
    try:
        return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_nonfinite)
    except (ValueError, UnicodeError) as exc:
        raise InvalidCandidate("invalid GitHub metadata JSON") from exc


def audit(run_id, artifact_id, race_code, expected_sha256, token, opener=None):
    if type(run_id) is not int or run_id <= 0 or type(artifact_id) is not int or artifact_id <= 0:
        raise InvalidCandidate("run/artifact IDs must be positive integers")
    if not isinstance(race_code, str) or not re.fullmatch(r"20[0-9]{10}", race_code):
        raise InvalidCandidate("race code malformed")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise InvalidCandidate("candidate digest malformed")
    if not isinstance(token, str) or not token:
        raise InvalidCandidate("read-only GitHub token required")
    opener = opener or build_opener(NoAuthCrossHostRedirect())
    def get(path, media):
        request = Request(API + path, headers={
            "Authorization": "Bearer " + token, "Accept": media,
            "User-Agent": "boat-edge-clean-formal-audit/1.0"})
        try:
            with opener.open(request, timeout=15) as response:
                data = response.read(2_000_001)
        except (HTTPError, URLError, TimeoutError, OSError):
            raise InvalidCandidate("GitHub artifact retrieval failed") from None
        if len(data) > 2_000_000:
            raise InvalidCandidate("GitHub response oversized")
        return data
    run = _strict_metadata_json(get(f"/actions/runs/{run_id}", "application/vnd.github+json"))
    listing = _strict_metadata_json(get(f"/actions/runs/{run_id}/artifacts?per_page=100", "application/vnd.github+json"))
    if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] != run_id:
        raise InvalidCandidate("GitHub run metadata mismatch")
    workflow_path = run.get("path")
    if workflow_path not in (".github/workflows/fresh-prospective-capture.yml",
                             ".github/workflows/fresh-prospective-capture.yml@refs/heads/main"):
        raise InvalidCandidate("unexpected workflow source")
    if run.get("head_branch") != "main":
        raise InvalidCandidate("capture run not on default branch")
    origin = run.get("head_repository")
    if not isinstance(origin, dict) or origin.get("full_name") != "ikst2512-eng/boat-edge-clean":
        raise InvalidCandidate("unexpected workflow repository")
    artifacts = listing.get("artifacts") if isinstance(listing, dict) else None
    if (not isinstance(artifacts, list) or type(listing.get("total_count")) is not int or
            listing["total_count"] != len(artifacts)) :
        raise InvalidCandidate("artifact listing incomplete")
    matches = [a for a in artifacts if isinstance(a, dict) and a.get("id") == artifact_id]
    if len(matches) != 1:
        raise InvalidCandidate("artifact not in specified run")
    if type(matches[0].get("id")) is not int:
        raise InvalidCandidate("artifact ID type invalid")
    artifact = matches[0]
    association = artifact.get("workflow_run")
    if not isinstance(association, dict) or type(association.get("id")) is not int or association["id"] != run_id:
        raise InvalidCandidate("artifact run association invalid")
    archive = get(f"/actions/artifacts/{artifact_id}/zip", "application/vnd.github+json")
    inspected = inspect_downloaded_artifact(archive, race_code, expected_sha256)
    if inspected["workflow_run_id"] != run_id:
        raise InvalidCandidate("downloaded receipt belongs to another run")
    if inspected["candidate_sha256"] != expected_sha256 or inspected["race_code"] != race_code:
        raise InvalidCandidate("downloaded evidence does not match requested candidate")
    metadata = inspect_actions_artifact(
        {"generated_at": inspected["generated_at"], "deadline_at": inspected["deadline_at"]},
        {"workflow_run_id": inspected["workflow_run_id"], "workflow_attempt": inspected["workflow_attempt"]},
        run, artifact)
    return {"artifact_zip_consistent": inspected["downloaded_bytes_consistent"],
            "github_run_id": run.get("id"), "artifact_id": artifact_id,
            "receipt_run_binding_verified": metadata["github_artifact_metadata_consistent"],
            "independent_upload_time_verified": False, "formal_approved": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--artifact-id", type=int, required=True)
    p.add_argument("--race-code", required=True)
    p.add_argument("--candidate-sha256", required=True)
    a = p.parse_args()
    print(json.dumps(audit(a.run_id, a.artifact_id, a.race_code,
                           a.candidate_sha256, os.environ.get("GITHUB_TOKEN", ""))))
