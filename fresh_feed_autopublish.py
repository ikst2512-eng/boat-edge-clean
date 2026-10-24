"""Build an immutable extension of predictions.json after a successful GitHub witness run.

Invoked by the workflow_run completion workflow, never by a forecast producer.
No predictions are generated or altered; the 120-way committed distribution is
verified by the publisher against GitHub's raw commit and run metadata.
"""
import argparse
import json
from pathlib import Path
from fresh_feed_builder import canonical
from fresh_feed_incremental import merge
from fresh_feed_publisher import assemble

def extend(existing_path, race_code, source_sha, run_id, deadline_at, resolver=assemble):
    path=Path(existing_path)
    original=json.loads(path.read_bytes()) if path.exists() else {}
    if not isinstance(original,dict):
        raise ValueError("invalid existing feed")
    candidate=resolver(source_sha,race_code,deadline_at,run_id)
    key=f"{race_code[:8]}-{race_code[8:10]}-{int(race_code[10:])}"
    merged,added,unchanged=merge(original,{key:candidate})
    if not added:
        raise ValueError("no new race to publish")
    output=canonical(merged)
    if len(output)>16_000_000:
        raise ValueError('active forecast feed exceeds API serving capacity')
    return output,added

def stage(existing_path,output_path,race_code,source_sha,run_id,deadline_at,resolver=assemble):
    existing=Path(existing_path);destination=Path(output_path)
    if existing.resolve()==destination.resolve() or destination.exists():
        raise ValueError("must write an unused staging path")
    contents,added=extend(existing,race_code,source_sha,run_id,deadline_at,resolver)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as f:f.write(contents)
    return added

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for field in ("existing","out","race-code","commit","deadline"):p.add_argument("--"+field,required=True)
    p.add_argument("--run-id",type=int,required=True)
    a=p.parse_args()
    print(stage(a.existing,a.out,a.race_code,a.commit,a.run_id,a.deadline))
