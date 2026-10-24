"""Test witness-to-feed handoff without live GitHub access."""
import io,json,tempfile
from pathlib import Path
from unittest.mock import patch
from fresh_auto_finalize import collect_from_witness,finalize
SHA="a"*40
RUN={"head_sha":SHA,"event":"push","conclusion":"success","head_branch":"main",
     "path":".github/workflows/fresh-snapshot-witness.yml@refs/heads/main"}
FILES={"files":[{"filename":"fresh_snapshots/202610241201.json","status":"added"}]}
SOURCE={"race_code":"202610241201","deadline_at":"2026-10-24T12:00:00+09:00"}
class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
def fetch(url):
    return RUN if "/actions/runs/" in url else FILES
def resolver(sha,code,deadline,run_id):
    return {"race_code":code,"deadline_at":deadline,"freeze_proof":{"run_id":run_id}}
def urlopen(req,timeout=8):return Response(json.dumps(SOURCE).encode())
def reject(callback):
    try:callback()
    except (ValueError,FileExistsError):return
    raise AssertionError("unsafe witness accepted")
def check():
    with patch("urllib.request.urlopen",side_effect=urlopen):
        records=collect_from_witness(123,fetch,resolver)
        assert len(records)==1
        with tempfile.TemporaryDirectory() as d:
            old=Path(d)/"predictions.json";target=Path(d)/"new.json"
            report=finalize(123,old,target,fetch,resolver)
            assert report["total"]==1 and len(report["added"])==1
            assert "20261024-12-1" in json.loads(target.read_text())
            reject(lambda:finalize(123,old,target,fetch,resolver))
            old.write_bytes(target.read_bytes())
            reject(lambda:finalize(123,old,Path(d)/"same.json",fetch,resolver))
        wrong=dict(RUN,path=".github/workflows/fresh-proof-tests.yml")
        reject(lambda:collect_from_witness(123,lambda u:wrong if "/actions/runs/" in u else FILES,resolver))
        badfiles={"files":[{"filename":"fresh_snapshots/202610241201.json","status":"modified"}]}
        reject(lambda:collect_from_witness(123,lambda u:RUN if "/actions/runs/" in u else badfiles,resolver))
        badsource=dict(SOURCE,deadline_at=None)
        with patch("urllib.request.urlopen",return_value=Response(json.dumps(badsource).encode())):
            reject(lambda:collect_from_witness(123,fetch,resolver))
    print("Witness to feed finalization tests passed")
if __name__=="__main__":check()
