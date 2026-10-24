"""Convert a v5 120-way immutable snapshot into a GitHub-committable API record.

This builds ONLY the frozen source record, not a publishable predictions.json
or fake GitHub proof. Commit the exact output before deadline. A separate,
independently audited publisher must attach the proof after publication.
"""
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from itertools import permutations

VALID = {f"{a}-{b}-{c}" for a,b,c in permutations(range(1,7),3)}

def canonical(obj):
    return (json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")

def valid_race_code(code):
    if not isinstance(code,str) or not re.fullmatch(r"[0-9]{12}",code):
        return False
    try:
        datetime.strptime(code[:8],"%Y%m%d")
    except ValueError:
        return False
    return 1<=int(code[8:10])<=24 and 1<=int(code[10:12])<=12

def convert(snapshot_bytes, model_version):
    raw=json.loads(snapshot_bytes)
    digest=raw.get("sha256")
    body={k:v for k,v in raw.items() if k!="sha256"}
    if not isinstance(digest,str) or hashlib.sha256(canonical(body)).hexdigest()!=digest:
        raise ValueError("v5 snapshot digest mismatch")
    if raw.get("schema")!="boatrace-fresh-v1" or not valid_race_code(raw.get("race_code")):
        raise ValueError("bad snapshot schema or code")
    probs=raw.get("probabilities")
    if not isinstance(probs,dict) or set(probs)!=VALID:
        raise ValueError("all 120 triples required")
    if any(type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1 for p in probs.values()):
        raise ValueError("invalid probabilities")
    if abs(sum(probs.values())-1)>1e-8:
        raise ValueError("non-normalized probabilities")
    generated=datetime.fromisoformat(raw["frozen_at_utc"])
    deadline=datetime.fromisoformat(raw["deadline_utc"])
    if generated.tzinfo is None or deadline.tzinfo is None or not generated<deadline:
        raise ValueError("late or timezone-naive snapshot")
    if not isinstance(model_version,str) or not 1<=len(model_version)<=80:
        raise ValueError("model version missing")
    ordered=sorted(VALID,key=lambda t:(-probs[t],tuple(map(int,t.split("-")))))
    record={"race_code":raw["race_code"],"generated_at":generated.isoformat(),
            "model_version":model_version,"validated":True,"deadline_at":deadline.isoformat(),
            "predictions":[{"ticket":t,"probability":probs[t]} for t in ordered[:10]],
            "probabilities":probs,"source_snapshot_sha256":digest}
    return record

def build(input_path,output_dir,model_version):
    path=Path(input_path)
    record=convert(path.read_bytes(),model_version)
    dest=Path(output_dir)/f'{record["race_code"]}.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Refuse overwrites; this is only a candidate for actual predeadline commit.
    with dest.open("xb") as f:
        f.write(canonical(record))
    return dest

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("snapshot")
    p.add_argument("--out-dir",default="fresh_snapshots")
    p.add_argument("--model-version",required=True)
    args=p.parse_args()
    print(build(args.snapshot,args.out_dir,args.model_version))
