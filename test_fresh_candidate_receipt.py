"""Prospective receipt is audit-only and binds exact candidate bytes."""
import json,tempfile,hashlib
from pathlib import Path
from datetime import datetime,timezone
from fresh_candidate_receipt import receipt
from fresh_feed_builder import canonical
def check():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"202610241201.json"
        body={"race_code":"202610241201","validated":True,
              "source_snapshot_sha256":"b"*64,
              "deadline_at":"2026-10-24T03:00:00+00:00"}
        path.write_bytes(canonical(body))
        result=receipt(path,"123","1",datetime(2026,10,24,2,20,tzinfo=timezone.utc))
        assert result["candidate_sha256"]==hashlib.sha256(path.read_bytes()).hexdigest()
        assert result["source_snapshot_sha256"]=="b"*64
        assert result["workflow_run_id"]==123
        assert result["independent_github_arrival_verified"] is False
        assert result["status"]=="candidate_only_not_formal_or_public"
        for broken in ("0","xyz"):
            try:receipt(path,broken,"1")
            except ValueError:pass
            else:raise AssertionError("invalid run id accepted")
        body["freeze_proof"]={"run_id":123}
        path.write_bytes(canonical(body))
        try:receipt(path,"123","1")
        except ValueError:pass
        else:raise AssertionError("public record accepted as candidate")
    workflow=Path(".github/workflows/fresh-prospective-capture.yml").read_text()
    assert "prospective_receipt.json" in workflow
    assert "fresh_candidate_receipt.py" in workflow
    print("Prospective audit receipt test passed")
if __name__=="__main__":check()
