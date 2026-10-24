import hashlib,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
from capture_fresh_candidates import capture
from fresh_feed_builder import canonical,VALID
P={t:1/120 for t in VALID}
def make(code="202610241201",deadline="2026-10-24T03:00:00+00:00"):
    body={"schema":"boatrace-fresh-v1","race_code":code,
      "frozen_at_utc":"2026-10-24T02:00:00+00:00",
      "deadline_utc":deadline,"probabilities":P}
    return canonical({**body,"sha256":hashlib.sha256(canonical(body)).hexdigest()})
def check():
    now=datetime(2026,10,24,2,20,tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);inbox=root/"in";out=root/"out";inbox.mkdir()
        (inbox/"202610241201.json").write_bytes(make())
        assert capture(inbox,out,"v5-offline-fixture",now)["saved"]==1
        frozen=(out/"202610241201.json").read_bytes()
        assert capture(inbox,out,"v5-offline-fixture",now)["already_saved"]==1
        assert (out/"202610241201.json").read_bytes()==frozen
        assert capture(inbox,out,"v5-offline-fixture",datetime(2026,10,24,2,55,tzinfo=timezone.utc))["rejected"]==1
        (inbox/"202610241202.json").write_bytes(make())
        assert capture(inbox,out,"v5-offline-fixture",now)["rejected"]>=1
        altered=make("202610241201","2026-10-24T04:00:00+00:00")
        (inbox/"202610241201.json").write_bytes(altered)
        assert capture(inbox,out,"v5-offline-fixture",now)["rejected"]>=1
        assert (out/"202610241201.json").read_bytes()==frozen
        (inbox/"202610241201.json").write_bytes(b'{"invalid":true}')
        assert capture(inbox,out,"v5-offline-fixture",now)["rejected"]>=1
    print("Fresh candidate capture checks passed")
if __name__=="__main__":check()
