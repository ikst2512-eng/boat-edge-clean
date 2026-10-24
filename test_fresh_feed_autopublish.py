import json,tempfile
from unittest.mock import patch
from pathlib import Path
from fresh_feed_autopublish import stage,extend
from fresh_feed_builder import canonical

EXISTING={"20261024-12-1":{"race_code":"202610241201","validated":True}}
RECORD={"race_code":"202610241202","validated":True,"freeze_proof":{"run_id":999}}
def resolver(sha,code,deadline,run_id):
    assert (sha,code,run_id)==("a"*40,"202610241202",999)
    return RECORD
def check():
    with tempfile.TemporaryDirectory() as d:
        base=Path(d);original=base/"predictions.json";destination=base/"staged.json"
        original.write_bytes(canonical(EXISTING))
        before=original.read_bytes()
        added=stage(original,destination,"202610241202","a"*40,999,"2026-10-24T12:00:00+09:00",resolver)
        assert added==["20261024-12-2"]
        written=json.loads(destination.read_bytes())
        assert written["20261024-12-1"]==EXISTING["20261024-12-1"]
        assert original.read_bytes()==before
        with patch("fresh_feed_autopublish.canonical",return_value=b"x"*16_000_001):
            try:extend(original,"202610241202","a"*40,999,"2026-10-24T12:00:00+09:00",resolver)
            except ValueError:pass
            else:raise AssertionError("oversize publication permitted")
        try:stage(original,destination,"202610241202","a"*40,999,"2026-10-24T12:00:00+09:00",resolver)
        except ValueError:pass
        else:raise AssertionError("staging path overwritten")
        original.write_bytes(destination.read_bytes())
        try:extend(original,"202610241202","a"*40,999,"2026-10-24T12:00:00+09:00",resolver)
        except ValueError:pass
        else:raise AssertionError("duplicate accepted")
    print("Fresh autopublish immutable addition tests passed")
if __name__=="__main__":check()
