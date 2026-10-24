import json
import tempfile
from pathlib import Path
from fresh_feed_isolated import collect,publish

ENTRIES=[
 {"commit_sha":"a"*40,"race_code":"202610241201","deadline_at":"2026-10-24T16:00:00+09:00","run_id":123},
 {"commit_sha":"b"*40,"race_code":"202610241202","deadline_at":"2026-10-24T16:05:00+09:00","run_id":124}]
def resolve(sha,code,deadline,run_id):
    if code.endswith("02"): raise ValueError("invalid proof")
    return {"race_code":code,"freeze_proof":{"commit_sha":sha}}
def check():
    accepted,rejected=collect(ENTRIES,resolve)
    assert len(accepted)==1 and rejected==[{"race_code":"202610241202","reason":"ValueError"}]
    try: collect(ENTRIES+[ENTRIES[0]],resolve)
    except ValueError: pass
    else: raise AssertionError("duplicate accepted")
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);manifest=root/"manifest.json";feed=root/"feed.json";audit=root/"audit.json"
        manifest.write_text(json.dumps(ENTRIES))
        assert publish(manifest,feed,audit,resolve)==(1,1)
        assert len(json.loads(feed.read_text()))==1
        assert json.loads(audit.read_text())["independent_timestamp_verified"] is False
        before=feed.read_bytes()
        try: publish(manifest,feed,audit,resolve)
        except FileExistsError: pass
        else:raise AssertionError("overwrite succeeded")
        assert feed.read_bytes()==before
    print("Isolated feed publication checks passed")
if __name__=="__main__":check()
