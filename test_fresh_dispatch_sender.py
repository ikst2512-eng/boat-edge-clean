import hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import canonical,VALID
from fresh_dispatch_sender import prepare,send
def fixture():
    b={"schema":"boatrace-fresh-v1","race_code":"202610241201",
       "frozen_at_utc":"2026-10-24T02:00:00+00:00",
       "deadline_utc":"2026-10-24T03:00:00+00:00",
       "probabilities":{t:1/120 for t in VALID}}
    return canonical({**b,"sha256":hashlib.sha256(canonical(b)).hexdigest()})
def check():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"202610241201.json";path.write_bytes(fixture())
        payload=prepare(path,"v5-fixture",datetime(2026,10,24,2,20,tzinfo=timezone.utc))
        assert payload["event_type"]=="fresh_v5_snapshot"
        candidate=prepare(path,"v5-fixture",datetime(2026,10,24,2,20,tzinfo=timezone.utc),collection_only=True)
        assert candidate["event_type"]=="fresh_v5_candidate"
        assert len(payload["client_payload"]["snapshot_base64"])>100
        def reject(f):
            try:f()
            except ValueError:return
            raise AssertionError("accepted invalid dispatch")
        reject(lambda:prepare(path,"v5-fixture",datetime(2026,10,24,2,47,tzinfo=timezone.utc)))
        reject(lambda:send(payload,"",source_check=lambda:{"ready":True}))
        reject(lambda:send(payload,"test-token",source_check=lambda:{"ready":False,"reason":"FORMAL_FIRST100_NOT_FROZEN"}))
        class Response:
            status=204
            def __enter__(self):return self
            def __exit__(self,*_):pass
        calls=[]
        def opener(req,timeout):
            calls.append((req.get_method(),req.data))
            return Response()
        assert send(payload,"test-token",opener,source_check=lambda:{"ready":True})=="accepted_not_witnessed"
        assert send(candidate,"test-token",opener,candidate_check=lambda:{"ready":True})=="accepted_not_witnessed"
        reject(lambda:send(candidate,"test-token",opener,candidate_check=lambda:{"ready":False,"reason":"PRE_RESULT_GUARDS_NOT_CLOSED"}))
        assert len(calls)==2
        assert calls[0][0]=="POST"
        assert json.loads(calls[0][1])["event_type"]=="fresh_v5_snapshot"
    print("Fresh dispatch sender tests passed")
if __name__=="__main__":check()
