"""Verify actual downloaded GitHub Actions artifact ZIP against API metadata.

Requires caller supplied private artifact ZIP, run JSON and artifact listing.
Never treats a candidate as officially approved.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
from fresh_candidate_artifact_audit import check_artifact
from fresh_candidate_verify import verify

def verify_download(zip_path,receipt_path,run_path,listing_path,workdir):
    archive=Path(zip_path)
    receipt=json.loads(Path(receipt_path).read_bytes())
    run=json.loads(Path(run_path).read_bytes())
    listing=json.loads(Path(listing_path).read_bytes())
    evidence=check_artifact(receipt,run,listing)
    match=[a for a in listing["artifacts"] if a["id"]==evidence["artifact_id"]]
    if len(match)!=1:raise ValueError("artifact ID mismatch")
    expected=match[0]["digest"].removeprefix("sha256:")
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError("download ZIP SHA256 differs from GitHub digest")
    dest=Path(workdir)
    dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        candidate="prospective_candidates/"+receipt["race_code"]+".json"
        if sorted(names)!=sorted([candidate,"prospective_receipt.json"]):
            raise ValueError("unexpected ZIP entries")
        if any(z.getinfo(n).file_size>100000 for n in names):
            raise ValueError("oversized evidence")
        saved=z.read(candidate)
        saved_receipt=z.read("prospective_receipt.json")
    if saved_receipt!=Path(receipt_path).read_bytes():
        raise ValueError("downloaded receipt differs from supplied receipt")
    p=dest/(receipt["race_code"]+".json");q=dest/"receipt.json"
    p.write_bytes(saved);q.write_bytes(saved_receipt)
    checked=verify(p,q)
    return {**evidence,**checked,"candidate_bytes_independently_verified":True,
            "formal_approved":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for x in ("zip_path","receipt","run","listing","workdir"):p.add_argument(x)
    a=p.parse_args()
    print(json.dumps(verify_download(a.zip_path,a.receipt,a.run,a.listing,a.workdir),sort_keys=True))
