#!/usr/bin/env python3
"""Read-only legacy workflow dependency matrix. Never deletes/stops workflows."""
import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

REPO = "ikst2512-eng/boat-edge"
API = "https://api.github.com/repos/" + REPO
RISK = re.compile(r"fresh|prediction|evidence|capture|audit|site|pages|odds|result|research|publish|auto.update", re.I)


def request_json(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "clean-workflow-audit"}
    if os.getenv("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def inventory(tree, runs):
    workflows = sorted(x["path"] for x in tree["tree"] if x.get("type") == "blob"
                       and x["path"].startswith(".github/workflows/")
                       and x["path"].endswith((".yml", ".yaml")))
    observed = {}
    for run in runs:
        path = run.get("path")
        if path in workflows and path not in observed:
            observed[path] = {"last_seen": run.get("created_at"), "conclusion": run.get("conclusion")}
    return {"schema": "CLEAN_LEGACY_WORKFLOW_ACTIVITY_V1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "legacy_tree_sha": tree["sha"], "runs_sampled": len(runs),
            "workflow_count": len(workflows), "recently_seen_count": len(observed),
            "not_seen_in_sample_count": len(workflows) - len(observed),
            "delete_authorized": False,
            "workflows": [
                {"path": path, "activity": observed.get(path),
                 "requires_source_dependency_inspection": True,
                 "sensitive_keyword_present": bool(RISK.search(path)),
                 "delete_authorized": False}
                for path in workflows
            ]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="legacy_workflow_inventory.json")
    args = p.parse_args()
    tree = request_json(API + "/git/trees/main?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("truncated source tree")
    runs = request_json(API + "/actions/runs?per_page=100")["workflow_runs"]
    document = inventory(tree, runs)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: document[k] for k in
                      ("workflow_count", "recently_seen_count", "not_seen_in_sample_count")}))


if __name__ == "__main__":
    main()
