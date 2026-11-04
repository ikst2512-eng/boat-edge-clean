"""Read-only inventory of four-mode scheduled capture runs.

Summarizes GitHub's own scheduled-run execution states. It does not infer
forecast publication or predeadline provenance from job success.
"""
import argparse
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

WORKFLOW = "four-mode-prospective-capture.yml"

def inventory(repo, token, fetch=None, limit=20):
    if not repo or "/" not in repo or not token or not 1 <= limit <= 100:
        raise ValueError("invalid inventory arguments")
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/"
           f"{quote(WORKFLOW)}/runs?event=schedule&per_page={limit}")
    if fetch is None:
        def fetch(u):
            req = Request(u, headers={"Authorization": "Bearer " + token,
                                      "Accept": "application/vnd.github+json",
                                      "User-Agent": "boat-edge-clean-inventory"})
            with urlopen(req, timeout=15) as response:
                return json.load(response)
    payload = fetch(url)
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("invalid GitHub response")
    runs = []
    unavailable_job_details = []
    for x in payload["workflow_runs"]:
        if not isinstance(x, dict) or x.get("event") != "schedule":
            raise ValueError("unexpected workflow event")
        if not isinstance(x.get("id"), int) or x["id"] <= 0:
            raise ValueError("invalid run id")
        try:
            job_data = fetch(f"https://api.github.com/repos/{repo}/actions/runs/{x['id']}/jobs?per_page=100")
        except HTTPError as exc:
            # GitHub may forbid/throttle per-run jobs even after the scheduled
            # run listing succeeded. Preserve observed run metadata, but never
            # infer that the capture job passed or that an archive was saved.
            if exc.code not in (403, 429):
                raise
            unavailable_job_details.append({"run_id": x["id"], "http_status": exc.code})
            runs.append({"id": x["id"], "created_at": x.get("created_at"),
                         "capture_conclusion": None, "failed_steps": None,
                         "job_details_status": "http_unavailable",
                         "status": x.get("status"), "conclusion": x.get("conclusion"),
                         "html_url": x.get("html_url")})
            continue
        if not isinstance(job_data, dict) or not isinstance(job_data.get("jobs"), list):
            raise ValueError("invalid GitHub jobs response")
        captures = [j for j in job_data["jobs"] if isinstance(j, dict) and j.get("name") == "capture"]
        if len(captures) != 1:
            raise ValueError("missing or duplicate capture job")
        capture = captures[0]
        steps = capture.get("steps")
        if not isinstance(steps, list):
            raise ValueError("missing capture steps")
        failures = [step.get("name") for step in steps
                    if isinstance(step, dict) and step.get("conclusion") == "failure"]
        runs.append({"id": x["id"], "created_at": x.get("created_at"),
                     "capture_conclusion": capture.get("conclusion"),
                     "failed_steps": failures,
                     "job_details_status": "verified",
                     "status": x.get("status"), "conclusion": x.get("conclusion"),
                     "html_url": x.get("html_url")})
    return {"schema": "FOUR_MODE_SCHEDULE_HISTORY_V1",
            "scheduled_run_count": len(runs), "runs": runs,
            "job_details_complete": not unavailable_job_details,
            "job_details_unavailable": unavailable_job_details,
            "v2_saved_proven": False, "model_accuracy_proven": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = inventory(args.repo, os.environ.get("GITHUB_TOKEN", ""))
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("FOUR_MODE_SCHEDULE_HISTORY=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Four-mode scheduled run inventory (read-only)\n")
            f.write(f"- Scheduled runs inspected: {len(result['runs'])}\n")
            for x in result["runs"]:
                f.write(f"- Run {x['id']}: {x['created_at']} — {x['status']} / {x['conclusion']}; failed={x['failed_steps']}\n")
            f.write("- V2 publication confirmed: **no** (requires Git commit/source audit)\n")
            f.write(f"- Detailed job coverage complete: **{result['job_details_complete']}**\n")
    if not result["job_details_complete"]:
        raise SystemExit("INCOMPLETE: GitHub HTTP 403/429 blocked capture job verification; metadata retained, not PASS")

if __name__ == "__main__":
    main()
