"""Read-only GitHub Actions capture-artifact inventory; never counts as formal accuracy."""
import io
import json
import os
import urllib.request
import urllib.error
import zipfile

def inspect_capture(data):
    if not isinstance(data,dict):
        return {"status":"invalid_json"}
    records=data.get("records")
    if not isinstance(records,list):
        return {"status":data.get("status","missing_records"),"records":0,"frozen":0,"bundle2":0}
    return {"status":data.get("status"),"records":len(records),
            "frozen":sum(x.get("status")=="shadow_frozen_unverified" for x in records),
            "bundle2":sum(x.get("status")=="shadow_frozen_unverified"
                and isinstance(x.get("shadow_bundle2"),list) for x in records)}

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
        rows.append(info)
    return {"schema":"HOLE_CAPTURE_ARTIFACT_INVENTORY_V1","status":"inventory_only",
            "formal":False,"production_forecast_changed":False,
            "independent_first_receipt_verified":False,"runs":rows,
            "total_frozen":sum(x["shadow"].get("frozen",0) for x in rows),
            "total_bundle2":sum(x["shadow"].get("bundle2",0) for x in rows),
            "warning":"Uploaded evidence is not independent first-receipt proof. Repeated run artifacts may represent the same race."}

if __name__=="__main__":
    print(json.dumps(run(os.environ["GITHUB_REPOSITORY"],os.environ["GH_TOKEN"]),
                     ensure_ascii=False,sort_keys=True))
