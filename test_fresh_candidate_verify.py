import hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import VALID,canonical,convert
from fresh_candidate_receipt import receipt
from fresh_candidate_verify import verify

def check():
    core={"schema":"boatrace-fresh-v1","race_code":"202610241201",
      "frozen_at_utc":"2026-10-24T02:00:00+00:00","deadline_utc":"2026-10-24T03:00:00+00:00",
      "probabilities":{t:1/120 for t in VALID}}
    raw=canonical({**core,"sha256":hashlib.sha256(canonical(core)).hexdigest()})
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"202610241201.json"; q=Path(d)/"audit.json"
        p.write_bytes(canonical(convert(raw,"external-v5-fixture")))
        q.write_bytes(canonical(receipt(p,123,1,datetime(2026,10,24,2,20,tzinfo=timezone.utc))))
        assert verify(p,q)["candidate_intact"] is True
        changed=json.loads(q.read_bytes());changed["candidate_sha256"]="0"*64
        q.write_bytes(canonical(changed))
        try:verify(p,q)
        except ValueError:pass
        else:raise AssertionError("forged receipt accepted")
    print("Candidate byte-integrity verification PASS")

if __name__=="__main__":check()
