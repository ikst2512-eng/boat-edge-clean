"""Read-only inventory of real GitHub Actions T12 dispatches and their artifacts.

Never mistake a PR regression check for a real-race observation.
"""
import argparse
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WORKFLOW = "official-joint-t12-dispatch.yml"


def inventory(repo, token, fetch=None, max_pages=5):
    if not token:
        raise ValueError("GitHub token is required; no unverified inventory")
    if not 1 <= max_pages <= 20:
        raise ValueError("invalid page bound")

    def request(url):
        if fetch is not None:
            return fetch(url)
        req = Request(url, headers={"Authorization": "Bearer " + token,
                                    "Accept": "application/vnd.github+json",
                                    "X-GitHub-Api-Version": "2022-11-28"})
        with urlopen(req, timeout=20) as response:
            return json.load(response)

    base = "https://api.github.com/repos/" + repo
    runs = []
    seen = set()
    truncated = False
    for page in range(1, max_pages + 1):
        url = base + "/actions/workflows/" + WORKFLOW + "/runs?" + urlencode(
            {"event": "workflow_dispatch", "per_page": 100, "page": page})
        data = request(url)
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
            raise ValueError("invalid workflow runs response")
        batch = data["workflow_runs"]
        for run in batch:
            if run.get("event") != "workflow_dispatch" or not isinstance(run.get("id"), int):
                raise ValueError("unverified run identity")
            if run["id"] in seen:
                raise ValueError("duplicate run in API pagination")
            seen.add(run["id"])
            artifacts = []
            for artifact_page in range(1, 21):
                artifacts_url = base + "/actions/runs/" + str(run["id"]) + "/artifacts?" + urlencode(
                    {"per_page": 100, "page": artifact_page})
                artifacts_data = request(artifacts_url)
                if not isinstance(artifacts_data, dict) or not isinstance(artifacts_data.get("artifacts"), list):
                    raise ValueError("invalid artifact inventory response")
                artifact_batch = artifacts_data["artifacts"]
                artifacts.extend(a for a in artifact_batch
                                 if a.get("name") == "official-joint-" + str(run["id"])
                                 and a.get("expired") is False)
                total_count = artifacts_data.get("total_count")
                if total_count is not None and (
                        not isinstance(total_count, int) or isinstance(total_count, bool)
                        or total_count < 0):
                    raise ValueError("invalid artifact total count")
                if len(artifact_batch) < 100:
                    if total_count is not None and 100 * (artifact_page - 1) + len(artifact_batch) < total_count:
                        raise ValueError("incomplete artifact pagination")
                    break
            else:
                raise ValueError("artifact list exceeds safe pagination bound")
            runs.append({"run_id": run["id"], "status": run.get("status"),
                         "conclusion": run.get("conclusion"),
                         "created_at": run.get("created_at"),
                         "matching_unexpired_artifact_ids": [
                             a["id"] for a in artifacts if isinstance(a.get("id"), int)]})
        if len(batch) < 100:
            break
    else:
        truncated = True
    return {"scope": "workflow_dispatch only; metadata inventory, not source proof",
            "repo": repo, "workflow": WORKFLOW,
            "real_dispatch_runs_seen": len(runs),
            "runs_with_matching_unexpired_artifacts": sum(
                bool(r["matching_unexpired_artifact_ids"]) for r in runs),
            "pagination_may_be_truncated": truncated,
            "t12_complete_pairs_verified": None,
            "historical_success_rate": None,
            "runs": runs}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--max-pages", type=int, default=5)
    args = p.parse_args()
    result = inventory(args.repo, os.environ.get("GITHUB_TOKEN"), max_pages=args.max_pages)
    from pathlib import Path
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}, ensure_ascii=False))
