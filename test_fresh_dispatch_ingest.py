"""Offline tests of the external v5 repository dispatch handoff."""
import base64,hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import VALID,canonical
from fresh_dispatch_ingest import receive

def snapshot():
    body={"schema":"boatrace-fresh-v1","race_code":"202610241201",
          "frozen_at_utc":"2026-10-24T02:00:00+00:00",
          "deadline_utc":"2026-10-24T03:00:00+00:00",
          "probabilities":{t:1/120 for t in VALID}}
    return canonical({**body,"sha256":hashlib.sha256(canonical(body)).hexdigest()})
def check():
    now=datetime(2026,10,24,2,20,tzinfo=timezone.utc)
    message={"action":"fresh_v5_snapshot","client_payload":{
        "snapshot_base64":base64.b64encode(snapshot()).decode(),
        "model_version":"external-v5-fixture"}}
    def reject(payload,now=now,out=None):
        try:receive(json.dumps(payload).encode(),out,now)
        except (ValueError,FileExistsError):return
        raise AssertionError("unsafe dispatch accepted")
    with tempfile.TemporaryDirectory() as d:
        target=Path(d)/"frozen"
        filename=receive(json.dumps(message).encode(),target,now)
        assert Path(filename).exists()
        before=Path(filename).read_bytes()
        reject(message,out=target)
        assert Path(filename).read_bytes()==before
        reject(message,now=datetime(2026,10,24,2,50,tzinfo=timezone.utc),out=Path(d)/"late")
        reject(dict(message,action="irrelevant"),out=Path(d)/"wrong")
        bad=json.loads(json.dumps(message))
        bad["client_payload"]["snapshot_base64"]="$$bad"
        reject(bad,out=Path(d)/"invalid")
        assert len(json.loads(before)["probabilities"])==120
    print("External v5 dispatch ingestion tests passed")
if __name__=="__main__":check()
