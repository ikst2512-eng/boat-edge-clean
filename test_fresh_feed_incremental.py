"""Regression tests: incremental append, immutable old race, collision, no overwrite."""
import json
import tempfile
from pathlib import Path
from fresh_feed_incremental import merge,stage

OLD={"20261024-12-1":{"race_code":"202610241201","freeze_proof":{"commit_sha":"a"*40}}}
NEW={"race_code":"202610241202","freeze_proof":{"commit_sha":"b"*40}}
def resolve(sha,code,deadline,run_id):return NEW.copy()
def check():
    m,added,unchanged=merge(OLD,{"20261024-12-2":NEW})
    assert added==["20261024-12-2"] and not unchanged and m["20261024-12-1"]==OLD["20261024-12-1"]
    m,a,u=merge(OLD,OLD)
    assert not a and u==["20261024-12-1"]
    try:merge(OLD,{"20261024-12-1":dict(OLD["20261024-12-1"],model_version="changed")})
    except ValueError:pass
    else:raise AssertionError("old prediction overwritten")
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);existing=root/"published.json";manifest=root/"manifest.json"
        staged=root/"staged.json";audit=root/"audit.json"
        existing.write_text(json.dumps(OLD))
        manifest.write_text(json.dumps([{"race_code":"202610241202","commit_sha":"b"*40,"deadline_at":"2026-10-24T16:00:00+09:00","run_id":123}]))
        before=existing.read_bytes()
        report=stage(existing,manifest,staged,audit,resolve)
        assert report["added"]==["20261024-12-2"]
        assert report["deployment_status"]=="staged_not_published"
        assert existing.read_bytes()==before
        assert len(json.loads(staged.read_text()))==2
        try:stage(existing,manifest,staged,audit,resolve)
        except FileExistsError:pass
        else:raise AssertionError("staged output overwritten")
    print("Incremental feed staging tests passed")
if __name__=="__main__":check()
