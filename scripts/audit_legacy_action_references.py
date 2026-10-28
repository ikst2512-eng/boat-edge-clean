"""Read-only cross-workflow text reference audit. Never authorizes deletion."""
import base64
import json
import os
import urllib.request

ROOT = "https://api.github.com/repos/ikst2512-eng/boat-edge"

def fetch(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-actions-audit"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return json.load(r)

def audit(tree, loader):
    if tree.get("truncated"):
        raise ValueError("truncated tree")
    files = {x["path"]: x["sha"] for x in tree["tree"] if x.get("type") == "blob"
             and x["path"].startswith(".github/workflows/")
             and x["path"].endswith((".yml", ".yaml"))}
    bodies = {path: loader(path, sha) for path, sha in files.items()}
    records = []
    for path in sorted(files):
        name = path.split("/")[-1]
        references = sorted(other for other, content in bodies.items()
                            if other != path and (path in content or name in content))
        content = bodies[path]
        records.append({"path": path, "sha1": files[path], "referenced_by": references,
                        "manual": "workflow_dispatch:" in content,
                        "schedule": "schedule:" in content,
                        "workflow_run": "workflow_run:" in content,
                        "deletion_authorized": False})
    return {"schema": "CLEAN_LEGACY_ACTION_REFERENCES_V1",
            "legacy_tree_sha": tree["sha"], "count": len(records),
            "referenced_count": sum(bool(r["referenced_by"]) for r in records),
            "delete_authorized": False, "records": records}

def main():
    tree = fetch(ROOT + "/git/trees/main?recursive=1")
    def loader(path, sha):
        blob = fetch(ROOT + "/git/blobs/" + sha)
        if blob.get("sha") != sha or blob.get("encoding") != "base64":
            raise ValueError("blob mismatch")
        return base64.b64decode(blob["content"]).decode("utf-8")
    report = audit(tree, loader)
    with open("legacy_action_references.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"count": report["count"], "referenced_count": report["referenced_count"]}))

if __name__ == "__main__":
    main()
