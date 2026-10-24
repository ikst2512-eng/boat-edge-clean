"""Separation regression: prospective dispatch cannot route into public predictions."""
import base64,hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import canonical,VALID
from fresh_dispatch_ingest import receive
from fresh_formal_source_preflight import assess,assess_collection

def check():
    frozen={"schema":"boatrace-fresh-v1","race_code":"202610241201",
            "frozen_at_utc":"2026-10-24T02:00:00+00:00",
            "deadline_utc":"2026-10-24T03:00:00+00:00",
            "probabilities":{ticket:1/120 for ticket in VALID}}
    snapshot=canonical({**frozen,"sha256":hashlib.sha256(canonical(frozen)).hexdigest()})
    msg={"action":"fresh_v5_candidate","client_payload":{
        "snapshot_base64":base64.b64encode(snapshot).decode(),
        "model_version":"prospective-only-test"}}
    now=datetime(2026,10,24,2,20,tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        path=receive(json.dumps(msg).encode(),root/"candidate",now,expected_action="fresh_v5_candidate")
        assert Path(path).is_file()
        assert not (root/"predictions.json").exists()
        try:receive(json.dumps(msg).encode(),root/"public",now)
        except ValueError:pass
        else:raise AssertionError("prospective dispatch accepted by formal route")
    status={"guards":{"results_seen":False,"unlock":False,"scoring":False,"RESULT_UNLOCK_TOKEN":None},
            "formalFirst100":{"races":0,"freezeManifestSha":None},
            "connected":False,"predictions_ready":False}
    assert assess_collection(status)["ready"] is True
    assert assess(status)["ready"] is False
    workflow=Path(".github/workflows/fresh-prospective-capture.yml").read_text()
    assert "types: [fresh_v5_candidate]" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "--collection-only" in workflow
    assert "predictions.json" not in workflow
    assert "git push" not in workflow
    print("Nonpublic prospective capture boundary verified")
if __name__=="__main__":check()


def test_upload_cutoff_wiring():
    from pathlib import Path
    workflow=Path('.github/workflows/fresh-prospective-capture.yml').read_text()
    assert 'Recheck cutoff immediately before artifact upload' in workflow
    assert workflow.index('Recheck cutoff immediately before artifact upload') < workflow.index('actions/upload-artifact@v4')

if __name__ == '__main__':
    test_upload_cutoff_wiring()
