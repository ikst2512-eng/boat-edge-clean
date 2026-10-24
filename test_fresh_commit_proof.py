"""Unit tests for GitHub-backed immutable prediction verification."""
import hashlib
import io
import json
from unittest.mock import patch
from datetime import datetime
from server import verify_commit_proof

RECORD = {"race_code":"202610241201","generated_at":"2026-10-24T11:00:00+09:00","validated":True,
          "predictions":[{"ticket":"1-2-3"}],"model_version":"fixture"}
RAW = json.dumps(RECORD,sort_keys=True).encode()
SHA = hashlib.sha256(RAW).hexdigest()
PROOF = {"commit_sha":"a"*40,"path":"fresh_snapshots/202610241201.json",
         "sha256":SHA,"run_id":123,"deadline_at":"2026-10-24T12:00:00+09:00","committed_at":"2026-10-24T11:05:00+09:00"}
class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
def fetch_ok(request,timeout=5):
    url=request.full_url
    if "/commits/" in url:
        return Response(json.dumps({"commit":{"committer":{"date":"2026-10-24T02:05:00Z"}}}).encode())
    if "/actions/runs/" in url:
        return Response(json.dumps({"head_sha":"a"*40,"event":"push","conclusion":"success","created_at":"2026-10-24T02:07:00Z"}).encode())
    return Response(RAW)
def expect_reject(proof,record=RECORD,fetch=fetch_ok):
    try:
        with patch("server.urlopen", side_effect=fetch):
            verify_commit_proof(proof,record,"202610241201")
    except (ValueError, KeyError, OSError):
        return
    raise AssertionError("unsafe proof accepted")
def test_proof_checks():
    # The verifier imports urlopen in module scope.
    with patch("server.urlopen",side_effect=fetch_ok):
        verify_commit_proof(PROOF,RECORD,"202610241201")
    expect_reject({**PROOF,"path":"../secrets.json"})
    expect_reject({**PROOF,"path":"fresh_snapshots/202610241202.json"})
    expect_reject({**PROOF,"committed_at":"2026-10-24T11:06:00+09:00"})
    expect_reject({**PROOF,"sha256":"0"*64})
    expect_reject(PROOF,{**RECORD,"model_version":"tampered"})
    expect_reject(PROOF,{**RECORD,"race_code":"202610241202"})
    def late(req,timeout=5):
        if "/commits/" in req.full_url:
            return Response(json.dumps({"commit":{"committer":{"date":"2026-10-24T03:00:00Z"}}}).encode())
        return Response(RAW)
    expect_reject(PROOF,fetch=late)
    print("GitHub freeze proof checks passed")
if __name__=="__main__":
    test_proof_checks()
