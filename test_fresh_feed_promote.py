"""Offline checks for compare-and-swap GitHub promotion."""
import base64,hashlib,json,tempfile
from pathlib import Path
from fresh_feed_builder import canonical
from fresh_feed_promote import promote

OLD={"20261024-12-1":{"race_code":"202610241201","validated":True}}
NEW={**OLD,"20261024-12-2":{"race_code":"202610241202","validated":True}}
def check():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);staged=root/"new.json";audit=root/"audit.json"
        staged.write_bytes(canonical(NEW))
        audit.write_bytes(canonical({"deployment_status":"staged_not_published",
           "previous_sha256":hashlib.sha256(canonical(OLD)).hexdigest(),
           "new_sha256":hashlib.sha256(staged.read_bytes()).hexdigest()}))
        calls=[]
        def api(method,url,token,payload=None):
            calls.append((method,payload))
            if method=="GET":
                return {"type":"file","sha":"blobsha","content":base64.b64encode(canonical(OLD)).decode()}
            return {"commit":{"sha":"abcdef"}}
        result=promote(staged,audit,"staging","test-token",api)
        assert result["new_races"]==["20261024-12-2"]
        assert calls[1][1]["sha"]=="blobsha"
        assert base64.b64decode(calls[1][1]["content"])==staged.read_bytes()
        def reject(f):
            try:f()
            except (ValueError,FileNotFoundError):return
            raise AssertionError("unsafe publication accepted")
        reject(lambda:promote(staged,audit,"main","token",api))
        reject(lambda:promote(staged,audit,"staging","",api))
        def changed(method,url,token,payload=None):
            assert method=="GET"
            return {"type":"file","sha":"other","content":base64.b64encode(b'{}').decode()}
        reject(lambda:promote(staged,audit,"staging","token",changed))
        bad=dict(NEW);bad["20261024-12-1"]={"race_code":"202610241201","validated":False}
        staged.write_bytes(canonical(bad))
        audit.write_bytes(canonical({"deployment_status":"staged_not_published",
           "previous_sha256":hashlib.sha256(canonical(OLD)).hexdigest(),
           "new_sha256":hashlib.sha256(staged.read_bytes()).hexdigest()}))
        reject(lambda:promote(staged,audit,"staging","token",api))
    print("GitHub promotion CAS tests passed")
if __name__=="__main__":check()
