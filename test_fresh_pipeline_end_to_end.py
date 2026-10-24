"""Offline end-to-end integrity check: v5 -> published record -> API."""
import hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
from fresh_feed_builder import canonical,convert,VALID
from fresh_feed_autopublish import extend
from server import get_predictions

CODE="202610241201"
def check():
    p={t:1/120 for t in VALID}
    original={"schema":"boatrace-fresh-v1","race_code":CODE,
              "frozen_at_utc":"2026-10-24T02:00:00+00:00",
              "deadline_utc":"2026-10-24T03:00:00+00:00","probabilities":p}
    frozen=canonical({**original,"sha256":hashlib.sha256(canonical(original)).hexdigest()})
    record=convert(frozen,"v5-e2e-fixture")
    record["freeze_proof"]={"commit_sha":"a"*40,"run_id":999,
         "committed_at":"2026-10-24T02:02:00+00:00",
         "deadline_at":"2026-10-24T03:00:00+00:00",
         "path":"fresh_snapshots/"+CODE+".json","sha256":hashlib.sha256(canonical({k:v for k,v in record.items() if k!="freeze_proof"})).hexdigest()}
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        data,added=extend(root/"missing.json",CODE,"a"*40,999,record["deadline_at"],
                          lambda sha,code,deadline,run_id:record)
        assert added==["20261024-12-1"]
        (root/"predictions.json").write_bytes(data)
        with patch("server.ROOT",root),patch("server.verify_commit_proof") as verifier:
            status,answer=get_predictions({"hd":["20261024"],"jcd":["12"],"rno":["1"]})
            assert status==200 and answer["status"]=="available"
            assert answer["predictions"][0]=="1-2-3"
            assert verifier.call_count==1
            saved=json.loads(data)
            saved["20261024-12-1"]["predictions"][0]["probability"]=0.99
            (root/"predictions.json").write_bytes(canonical(saved))
            status,answer=get_predictions({"hd":["20261024"],"jcd":["12"],"rno":["1"]})
            assert status==503 and answer["status"]=="error"
            assert verifier.call_count==1
    print("Fresh snapshot to API end-to-end contract passed")
if __name__=="__main__":
    check()
