import hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import VALID,canonical
from fresh_prospective_sender import prepare,dispatch,verify_receiver_on_main

def check():
    core={"schema":"boatrace-fresh-v1","race_code":"202610241201",
          "frozen_at_utc":"2026-10-24T02:00:00+00:00","deadline_utc":"2026-10-24T03:00:00+00:00",
          "probabilities":{ticket:1/120 for ticket in VALID}}
    blob=canonical({**core,"sha256":hashlib.sha256(canonical(core)).hexdigest()})
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"202610241201.json";p.write_bytes(blob)
        payload=prepare(p,"candidate-test",datetime(2026,10,24,2,20,tzinfo=timezone.utc))
        assert payload["event_type"]=="fresh_v5_candidate"
        status={"guards":{"results_seen":False,"unlock":False,"scoring":False,"RESULT_UNLOCK_TOKEN":None}}
        class Response:
            status=204
            def __enter__(self):return self
            def __exit__(self,*_):pass
        sent=[]
        def opener(req,timeout):
            sent.append(json.loads(req.data))
            return Response()
        assert dispatch(payload,"test-secret",status,opener)=="accepted_not_frozen_or_witnessed"
        assert sent[0]["event_type"]=="fresh_v5_candidate"
        for bad in ({**payload,"event_type":"fresh_v5_snapshot"},payload):
            try:dispatch(bad,"test-secret",{**status,"guards":{**status["guards"],"scoring":True}},opener)
            except ValueError:pass
            else:raise AssertionError("unsafe event accepted")
        try:prepare(p,"candidate-test",datetime(2026,10,24,2,50,tzinfo=timezone.utc))
        except ValueError:pass
        else:raise AssertionError("late candidate accepted")
    class FakeJSON:
        def __init__(self,payload):self.payload=payload
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return json.dumps(self.payload).encode()
    good={"type":"file","path":".github/workflows/fresh-prospective-capture.yml"}
    assert verify_receiver_on_main(lambda req,timeout:FakeJSON(good))
    try:verify_receiver_on_main(lambda req,timeout:FakeJSON({"type":"dir"}))
    except ValueError:pass
    else:raise AssertionError("missing receiver accepted")
    print("Nonpublic sender verified")

if __name__=="__main__":check()
