import hashlib,json,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone
from fresh_feed_builder import canonical,convert,VALID
from fresh_candidate_receipt import receipt
from fresh_candidate_download_verify import verify_download

def run():
    core={"schema":"boatrace-fresh-v1","race_code":"202610241201",
          "frozen_at_utc":"2026-10-24T02:00:00+00:00","deadline_utc":"2026-10-24T03:00:00+00:00",
          "probabilities":{t:1/120 for t in VALID}}
    source=canonical({**core,"sha256":hashlib.sha256(canonical(core)).hexdigest()})
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);candidate=convert(source,"fixture")
        raw=canonical(candidate);rcpt=canonical(receipt(_make(root/"202610241201.json",raw),123,1,datetime(2026,10,24,2,20,tzinfo=timezone.utc)))
        archive=root/"evidence.zip"
        with zipfile.ZipFile(archive,"w") as z:
            z.writestr("prospective_candidates/202610241201.json",raw)
            z.writestr("prospective_receipt.json",rcpt)
        _make(root/"receipt.json",rcpt)
        run={"id":123,"run_attempt":1,"event":"repository_dispatch","conclusion":"success",
             "head_branch":"main","path":".github/workflows/fresh-prospective-capture.yml",
             "created_at":"2026-10-24T02:20:00Z"}
        listing={"artifacts":[{"id":44,"name":"prospective-v5-123","expired":False,
          "size_in_bytes":archive.stat().st_size,
          "digest":"sha256:"+hashlib.sha256(archive.read_bytes()).hexdigest(),
          "created_at":"2026-10-24T02:25:00Z","workflow_run":{"id":123}}]}
        _make(root/"run.json",canonical(run));_make(root/"listing.json",canonical(listing))
        args=(archive,root/"receipt.json",root/"run.json",root/"listing.json",root/"out")
        assert verify_download(*args)["candidate_bytes_independently_verified"] is True
        _make(archive,archive.read_bytes()+b"tamper")
        try:verify_download(*args)
        except ValueError:pass
        else:raise AssertionError("tampered ZIP accepted")
    print("Downloaded candidate artifact integrity PASS")

def _make(path,raw):
    path.write_bytes(raw);return path
if __name__=="__main__":run()
