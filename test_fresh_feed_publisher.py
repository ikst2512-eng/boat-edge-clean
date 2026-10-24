"""Offline simulated GitHub source tests for candidate feed publisher."""
import hashlib, io, json, tempfile
from pathlib import Path
from unittest.mock import patch
from fresh_feed_builder import VALID,canonical
from fresh_feed_publisher import assemble,write_new_feed

CODE="202610241201"
SHA="a"*40
P={t:1/120 for t in VALID}
PICKS=sorted(VALID,key=lambda t:tuple(map(int,t.split("-"))))
SOURCE={"race_code":CODE,"generated_at":"2026-10-24T02:00:00+00:00",
        "model_version":"fixture","validated":True,"deadline_at":"2026-10-24T12:00:00+09:00",
        "probabilities":P,"predictions":[{"ticket":t,"probability":P[t]} for t in PICKS[:10]]}
class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
def fake_fetch(url):
    if "/actions/runs/" in url:
        return {"head_sha":SHA,"event":"push","conclusion":"success","head_branch":"main","path":".github/workflows/fresh-snapshot-witness.yml","created_at":"2026-10-24T02:07:00Z"}
    return {"commit":{"committer":{"date":"2026-10-24T02:05:00Z"}}}
def fake_open(req,timeout=8):
    return Response(canonical(SOURCE))
def check():
    with patch("fresh_feed_publisher.fetch_json",side_effect=fake_fetch),patch("fresh_feed_publisher.urlopen",side_effect=fake_open):
        record=assemble(SHA,CODE,"2026-10-24T12:00:00+09:00",123)
        assert record["freeze_proof"]["sha256"]==hashlib.sha256(canonical(SOURCE)).hexdigest()
        assert len(record["probabilities"])==120
        assert record["deadline_at"]==SOURCE["deadline_at"]
        reject_deadline=lambda:assemble(SHA,CODE,"2026-10-24T13:00:00+09:00",123)
        try:reject_deadline()
        except ValueError:pass
        else:raise AssertionError("changed deadline accepted")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"predictions.json"
            write_new_feed(record,path)
            assert "20261024-12-1" in json.loads(path.read_text())
            try:write_new_feed(record,path)
            except FileExistsError:pass
            else:raise AssertionError("feed overwrite allowed")
        def reject(fn):
            try:fn()
            except (ValueError,TypeError,KeyError):return
            raise AssertionError("invalid proof accepted")
        reject(lambda:assemble("BAD",CODE,"2026-10-24T12:00:00+09:00",123))
        reject(lambda:assemble(SHA,CODE,"2026-10-24T11:00:00+09:00",123))
        bad=dict(SOURCE,race_code="202610241202")
        with patch("fresh_feed_publisher.urlopen",return_value=Response(canonical(bad))):
            reject(lambda:assemble(SHA,CODE,"2026-10-24T12:00:00+09:00"))
    print("Candidate feed publisher tests passed")
if __name__=="__main__":check()
