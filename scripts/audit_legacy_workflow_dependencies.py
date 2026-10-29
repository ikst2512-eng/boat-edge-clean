#!/usr/bin/env python3
"""Conservative legacy workflow references audit; never authorizes deletion."""
import base64
import json
import os
import re
import urllib.request

API = "https://api.github.com/repos/ikst2512-eng/boat-edge"


def fetch(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-dependency-audit"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        return json.load(response)


def inspect(workflows, contents):
    output = []
    for path in workflows:
        own = contents.get(path)
        name = path.rsplit("/", 1)[-1]
        incoming = sorted(p for p, body in contents.items() if p != path and name in body)
        outgoing = sorted(p for p in workflows if p != path and
                          p.rsplit("/", 1)[-1] in (own or ""))
        output.append({
            "path": path,
            "inspected": own is not None,
            "referenced_by_filename": incoming,
            "references_filename": outgoing,
            "manual_dispatch": bool(own and re.search(r"(?m)^\s*workflow_dispatch\s*:", own)),
            "schedule": bool(own and re.search(r"(?m)^\s*schedule\s*:", own)),
            "safe_to_delete": False,
            "warning": "Filename reference search is not complete dependency proof."
        })
    return output


def main():
    tree = fetch(API + "/git/trees/main?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("truncated Git tree")
    files = {x["path"]: x["sha"] for x in tree["tree"]
             if x.get("type") == "blob" and x["path"].startswith(".github/workflows/")
             and x["path"].endswith((".yml", ".yaml"))}
    contents = {}
    errors = {}
    for path, sha in sorted(files.items()):
        try:
            blob = fetch(API + "/git/blobs/" + sha)
            if blob.get("sha") != sha or blob.get("encoding") != "base64":
                raise ValueError("unexpected blob identity or encoding")
            contents[path] = base64.b64decode(blob["content"]).decode("utf-8")
        except (OSError, ValueError, KeyError, UnicodeError) as exc:
            errors[path] = str(exc)
    rows = inspect(sorted(files), contents)
    report = {"schema": "CLEAN_LEGACY_WORKFLOW_DEPENDENCIES_V1",
              "legacy_tree_sha": tree["sha"], "workflow_count": len(files),
              "inspected": len(contents), "inspection_errors": errors,
              "with_incoming_filename_references": sum(bool(r["referenced_by_filename"]) for r in rows),
              "delete_authorized": False, "workflows": rows}
    with open("legacy_workflow_dependencies.json", "w", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(json.dumps({k: report[k] for k in
                      ("workflow_count", "inspected", "with_incoming_filename_references")}))


if __name__ == "__main__":
    main()
