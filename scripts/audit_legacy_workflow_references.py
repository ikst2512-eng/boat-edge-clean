#!/usr/bin/env python3
"""Fail-closed read-only workflow filename reference audit."""
import base64,json,os,urllib.request

API="https://api.github.com/repos/ikst2512-eng/boat-edge"
def get(url):
    h={"Accept":"application/vnd.github+json","User-Agent":"clean-deps"}
    if os.getenv("GH_TOKEN"):h["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60) as r:return json.load(r)
def analyze(files,texts):
    return [{"path":p,"referenced_by":sorted(k for k,v in texts.items() if k!=p and p.split("/")[-1] in v),
             "manual_or_schedule_trigger":any(s in texts.get(p,"") for s in ("workflow_dispatch:","schedule:")),
             "read_success":p in texts,"delete_authorized":False} for p in sorted(files)]
def main():
    tree=get(API+"/git/trees/main?recursive=1")
    if tree.get("truncated"):raise ValueError("truncated tree")
    files={v["path"]:v["sha"] for v in tree["tree"] if v.get("type")=="blob" and v["path"].startswith(".github/workflows/") and v["path"].endswith((".yml",".yaml"))}
    texts={};errors={}
    for path,sha in files.items():
        try:
            b=get(API+"/git/blobs/"+sha)
            if b.get("sha")!=sha or b.get("encoding")!="base64":raise ValueError("blob identity mismatch")
            texts[path]=base64.b64decode(b["content"]).decode("utf-8")
        except (OSError,ValueError,UnicodeError,KeyError) as e:errors[path]=str(e)
    rows=analyze(files,texts)
    d={"schema":"CLEAN_LEGACY_WORKFLOW_REFERENCES_V1","tree_sha":tree["sha"],"workflow_count":len(rows),"read_errors":errors,
       "referenced_workflows":sum(bool(x["referenced_by"]) for x in rows),
       "warning":"No filename reference does NOT imply safe to delete; indirect dependencies remain.",
       "delete_authorized":False,"records":rows}
    with open("legacy_workflow_references.json","w") as f:json.dump(d,f,indent=2)
    print(json.dumps({"count":len(rows),"read_errors":len(errors),"referenced":d["referenced_workflows"]}))
if __name__=="__main__":main()
