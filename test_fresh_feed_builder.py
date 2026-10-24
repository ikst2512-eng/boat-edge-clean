"""Regression tests for v5 -> API frozen source conversion."""
import hashlib
from fresh_feed_builder import canonical,convert,VALID
def snapshot(p=None):
    if p is None:p={t:1/120 for t in VALID}
    raw={"schema":"boatrace-fresh-v1","race_code":"202610241201",
         "frozen_at_utc":"2026-10-24T02:00:00+00:00",
         "deadline_utc":"2026-10-24T03:00:00+00:00",
         "probabilities":p}
    raw["sha256"]=hashlib.sha256(canonical(raw)).hexdigest()
    return canonical(raw)
def check():
    result=convert(snapshot(),"v5-fixture")
    assert len(result["predictions"])==10
    assert len(result["probabilities"])==120
    assert result["predictions"][0]["ticket"]=="1-2-3"
    assert sum(result["probabilities"].values())>0.9999999
    assert "freeze_proof" not in result
    def reject(blob):
        try:convert(blob,"fixture")
        except ValueError:return
        raise AssertionError("invalid input accepted")
    bad=bytearray(snapshot());bad[-10]=ord('9');reject(bytes(bad))
    badprob={t:1/120 for t in VALID};badprob.pop("1-2-3");reject(snapshot(badprob))
    zero={t:0 for t in VALID};reject(snapshot(zero))
    print("Fresh feed builder tests passed")
if __name__=="__main__":check()
