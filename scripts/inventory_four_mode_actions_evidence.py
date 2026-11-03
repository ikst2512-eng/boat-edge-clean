"""Read-only GitHub Actions provenance inventory for four-mode publication and shadow capture.

A workflow being green is NOT evidence of a race-level successful freeze.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

WORKFLOW = "four-mode-prospective-capture.yml"


def api(path, token, repo):
    req = Request("https://api.github.com/repos/" + repo + "/" + path,
                  headers={"Accept": "application/vnd.github+json",
                           "Authorization": "Bearer " + token,
                           "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=20) as response:
        return json.load(response)


def inventory(repo, token, fetch=api, limit=15):
    if not token or not 1 <= limit <= 50:
        raise ValueError("missing_token_or_invalid_limit")
    # Query each event directly: frequent PR checks must not crowd out scheduled runs.
    runs = []
    for event in ("schedule", "workflow_dispatch"):
        batch = fetch(f"actions/workflows/{WORKFLOW}/runs?event={event}&per_page={limit}", token, repo)["workflow_runs"]
        runs.extend(batch)
    runs = list({run["id"]: run for run in runs}.values())
    runs.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    rows = []
    for run in runs:
        if run.get("event") not in ("schedule", "workflow_dispatch"):
            continue
        run_id = run["id"]
        artifacts = fetch(f"actions/runs/{run_id}/artifacts?per_page=100", token, repo)
        names = {a["name"] for a in artifacts.get("artifacts", []) if not a.get("expired", False)}
        record = {
            "run_id": run_id, "created_at": run.get("created_at"),
            "event": run.get("event"), "conclusion": run.get("conclusion"),
            "capture_artifact_present": any(x.startswith("four-mode-capture-") for x in names),
            "hole_shadow_file_contents_verified": False,
            "published_new_forecasts_verified": False,
        }
        # The artifact zip still needs an independent evidence-content check.
        record["evidence_verdict"] = "artifact_available_uninspected" if record["capture_artifact_present"] else "artifact_missing_or_expired"
        rows.append(record)
    return {"schema":"FOUR_MODE_ACTIONS_EVIDENCE_INVENTORY_V1",
            "status": "run_metadata_only", "formal": False,
            "independent_first_receipt_verified": False,
            "prospective_shadow_collection_verified": False,
            "queried_runs": len(runs), "eligible_runs": len(rows),
            "rows": rows,
            "warning": "Workflow run and artifact metadata cannot establish saved-new-prediction count, shadow content, or predeadline remote first receipt."}


if __name__ == "__main__":
    repo = os.environ["GITHUB_REPOSITORY"]
    report = inventory(repo, os.environ.get("GH_TOKEN"))
    path = Path("four-mode-run-evidence-inventory.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"status": report["status"], "queried_runs": report["queried_runs"],
                      "eligible_runs": report["eligible_runs"], "rows": report["rows"]},
                     ensure_ascii=False))
