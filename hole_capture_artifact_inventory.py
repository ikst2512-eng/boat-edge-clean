"""Read-only GitHub Actions capture-artifact inventory; never counts as formal accuracy."""
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
import urllib.request
import urllib.error
import zipfile
from hole_shadow_stage_verdict import classify

def inspect_capture(data):
    if not isinstance(data,dict):
        return {"status":"invalid_json"}
    records=data.get("records")
    if not isinstance(records,list):
        return {"status":data.get("status","missing_records"),"records":0,"frozen":0,"bundle2":0}
    return {"status":data.get("status"),"records":len(records),
            "frozen":sum(x.get("status")=="shadow_frozen_unverified" for x in records),
            "bundle2":sum(x.get("status")=="shadow_frozen_unverified"
                and isinstance(x.get("shadow_bundle2"),list) for x in records),
            # Presence means a locally declared snapshot, not a verified freeze.
            "future_locked_declared":sum(
                x.get("status")=="shadow_frozen_unverified"
                and isinstance(x.get("future_locked_candidates"),dict)
                and set(x["future_locked_candidates"])==
                    {"baseline","donor_order","max_ticket_score","third_national_rate"}
                and all(isinstance(v,list) for v in x["future_locked_candidates"].values())
                for x in records)}

def zip_shadow(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        matched=[name for name in archive.namelist()
                 if name.endswith("hole-shadow.json") and not name.startswith("__MACOSX/")]
        if not matched:
            return {"status":"no_hole_shadow_in_artifact"}
        if len(matched)>1:
            return {"status":"ambiguous_multiple_shadow_files"}
        name=matched[0]
        if archive.getinfo(name).file_size>2000000:
            return {"status":"oversize_shadow"}
        return inspect_capture(json.loads(archive.read(name)))

def api(url,token,accept="application/vnd.github+json"):
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,"Accept":accept,
        "X-GitHub-Api-Version":"2022-11-28","User-Agent":"hole-research-inventory"})
    with urllib.request.urlopen(req,timeout=25) as response:
        data=response.read(10000000)
    return data

def gh_shadow(run_id,repo,token):
    """Read a real Actions artifact via gh fallback and attribute a missing shadow.

    A self-declared publication verdict is research evidence, not remote proof.
    """
    with tempfile.TemporaryDirectory() as directory:
        env={**os.environ,"GH_TOKEN":token}
        result=subprocess.run(["gh","run","download",str(run_id),"--repo",repo,
                               "--pattern","four-mode-capture-*","--dir",directory],
                              capture_output=True,text=True,env=env,timeout=90)
        if result.returncode:
            return {"status":"cli_download_failed","exit_code":result.returncode}
        root=Path(directory)
        def get(name):
            found=[p for p in root.rglob(name) if p.is_file() and not p.is_symlink()]
            if not found or len(found)!=1 or found[0].stat().st_size>2000000:
                return None
            try:
                return json.loads(found[0].read_text(encoding="utf-8"))
            except (OSError,ValueError,UnicodeError):
                return None
        shadow=get("hole-shadow.json")
        publication=get("publication.json")
        stages=get("stages.json")
        analysis=inspect_capture(shadow) if shadow is not None else {
            "status":"no_hole_shadow_in_artifact"}
        analysis["stage_diagnosis"]=classify(stages,publication,shadow)
        analysis["publication_outcome"]=(
            publication.get("outcome") if isinstance(publication,dict) else None)
        analysis["staging_outcome"]=(
            stages.get("receipt_staging") if isinstance(stages,dict) else None)
        return analysis

def run(repo,token,limit=20):
    if not repo or not token:raise ValueError("missing_credentials")
    limit=min(max(int(limit),1),40)
    base="https://api.github.com/repos/"+repo
    runs=json.loads(api(base+"/actions/workflows/four-mode-prospective-capture.yml/runs?per_page="+str(limit),token))
    rows=[]
    for run in runs.get("workflow_runs",[]):
        if run.get("event") not in ("schedule","workflow_dispatch"):
            continue
        info={"run_id":run["id"],"created_at":run.get("created_at"),
              "conclusion":run.get("conclusion"),"shadow":{"status":"not_found"}}
        assets=json.loads(api(base+"/actions/runs/"+str(run["id"])+"/artifacts?per_page=100",token))
        found=[a for a in assets.get("artifacts",[]) if a.get("name","").startswith("four-mode-capture-") and not a.get("expired")]
        if found:
            artifact=found[0]
            info["artifact_id"]=artifact.get("id")
            try:
                blob=api(artifact["archive_download_url"],token,"application/octet-stream")
                info["shadow"]=zip_shadow(blob)
            except (OSError,ValueError,KeyError,zipfile.BadZipFile) as e:
                info["shadow"]={"status":"artifact_unreadable","error_type":type(e).__name__}
                if isinstance(e,urllib.error.HTTPError):
                    info["shadow"]["http_status"]=e.code
                    if e.code==415:
                        try:info["shadow"]=gh_shadow(run["id"],repo,token)
                        except (OSError,ValueError,subprocess.TimeoutExpired) as fallback:
                            info["shadow"]={"status":"cli_download_error",
                                            "error_type":type(fallback).__name__}
        rows.append(info)
    return {"schema":"HOLE_CAPTURE_ARTIFACT_INVENTORY_V1","status":"inventory_only",
            "formal":False,"production_forecast_changed":False,
            "independent_first_receipt_verified":False,"runs":rows,
            "total_frozen":sum(x["shadow"].get("frozen",0) for x in rows),
            "total_bundle2":sum(x["shadow"].get("bundle2",0) for x in rows),
            "total_future_locked_declared":sum(x["shadow"].get("future_locked_declared",0) for x in rows),
            "warning":"Uploaded evidence is not independent first-receipt proof. Repeated run artifacts may represent the same race."}

if __name__=="__main__":
    print(json.dumps(run(os.environ["GITHUB_REPOSITORY"],os.environ["GH_TOKEN"]),
                     ensure_ascii=False,sort_keys=True))
