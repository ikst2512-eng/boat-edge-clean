"""Multi-race feed assembly and refusal regression."""
import json
import tempfile
from pathlib import Path
from fresh_feed_batch import prepare,write_new_batch

ENTRIES=[{"commit_sha":"a"*40,"race_code":"202610241201","deadline_at":"2026-10-24T15:00:00+09:00","run_id":123},
         {"commit_sha":"b"*40,"race_code":"202610240902","deadline_at":"2026-10-24T15:05:00+09:00","run_id":124}]
def resolve(commit,code,deadline,run_id):
    return {"race_code":code,"freeze_proof":{"commit_sha":commit},"validated":True,
            "predictions":[{"ticket":"1-2-3"}]}
def rejects(f):
    try:f()
    except (ValueError,FileExistsError):return
    raise AssertionError("invalid manifest accepted")
def check():
    feed=prepare(ENTRIES,resolve)
    assert list(feed)==["20261024-09-2","20261024-12-1"]
    rejects(lambda:prepare(ENTRIES+[ENTRIES[0]],resolve))
    rejects(lambda:prepare([dict(ENTRIES[0],race_code="202610242501")],resolve))
    rejects(lambda:prepare([dict(ENTRIES[0],race_code="202610241213")],resolve))
    rejects(lambda:prepare([dict(ENTRIES[0],unknown=1)],resolve))
    rejects(lambda:prepare(ENTRIES,lambda a,b,c,d:{"race_code":"other","freeze_proof":{}}))
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp);manifest=base/"manifest.json";out=base/"feed.json"
        manifest.write_text(json.dumps(ENTRIES))
        assert write_new_batch(manifest,out,resolve)==2
        original=out.read_bytes()
        rejects(lambda:write_new_batch(manifest,out,resolve))
        assert out.read_bytes()==original
        another=base/"invalid.json"
        manifest.write_text(json.dumps([ENTRIES[0],ENTRIES[0]]))
        rejects(lambda:write_new_batch(manifest,another,resolve))
        assert not another.exists()
    print("Multi-race feed batch tests passed")
if __name__=="__main__":check()
