"""Read-only watchdog decision evidence from actual GitHub Actions job logs.

An accepted fallback dispatch and a later capture are distinct observations.
Never infer a parent-child trigger link or a successful archive publication.
"""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

MARKER = "FOUR_MODE_WATCHDOG="
ALLOWED = {"fallback_dispatch_accepted", "no_dispatch"}


def api(url, token, *, json_result=True):
    req = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "boat-edge-clean-watchdog-decisions"})
    with urlopen(req, timeout=20) as response:
        data = response.read(6_000_001)
    if len(data) > 6_000_000:
        raise ValueError("oversized GitHub response")
    if json_result:
        return json.loads(data)
    return data.decode("utf-8")


def parse_decision(log):
    if not isinstance(log, str):
        raise ValueError("invalid job log")
    rows = []
    for line in log.splitlines():
        if MARKER not in line:
            continue
        fragment = line.split(MARKER, 1)[1].strip()
        try:
            item = json.loads(fragment)
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict) and item.get("action") in ALLOWED:
            rows.append(item)
    # Multiple conflicting reports may be retries or pasted log text. Do not guess.
    if len(rows) != 1:
        return None
    item = rows[0]
    result = {"action": item["action"], "capture_hours_jst": item.get("capture_hours_jst"),
              "recent_publication_runs": item.get("recent_publication_runs"),
              "recent_healthy_or_active_runs": item.get("recent_healthy_or_active_runs"),
              "recent_failed_runs": item.get("recent_failed_runs"),
              "fallback_retry_cooldown": item.get("fallback_retry_cooldown"),
              "newest": item.get("newest")}
    return result


def inspect(history, repo, token, fetch=api, limit=6):
    if (not isinstance(history, dict) or not isinstance(history.get("recent_watchdog_runs"), list)
            or not repo or repo.count("/") != 1 or not token or not 1 <= limit <= 10):
        raise ValueError("invalid audit inputs")
    base = f"https://api.github.com/repos/{repo}"
    decisions = []
    for run in history["recent_watchdog_runs"][:limit]:
        if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0:
            raise ValueError("invalid watchdog run")
        record = {"run_id": run["id"], "created_at": run.get("created_at"),
                  "trigger_event": run.get("event"), "run_conclusion": run.get("conclusion"),
                  "decision": None, "evidence_status": "unavailable"}
        try:
            jobs = fetch(f"{base}/actions/runs/{run['id']}/jobs?per_page=100", token)
            candidates = [j for j in jobs.get("jobs", [])
                          if isinstance(j, dict) and j.get("name") == "watchdog"
                          and type(j.get("id")) is int]
            if len(candidates) != 1:
                record["evidence_status"] = "missing_or_duplicate_watchdog_job"
            elif candidates[0].get("conclusion") != "success":
                record["evidence_status"] = "watchdog_job_not_successful"
            else:
                log = fetch(f"{base}/actions/jobs/{candidates[0]['id']}/logs",
                            token, json_result=False)
                decision = parse_decision(log)
                if decision is None:
                    record["evidence_status"] = "decision_marker_unverified"
                else:
                    record["decision"] = decision
                    record["evidence_status"] = "watchdog_log_verified"
        except (OSError, ValueError, TypeError, KeyError) as exc:
            record["evidence_status"] = "retrieval_error:" + type(exc).__name__
        decisions.append(record)
    verified = [r for r in decisions if r["evidence_status"] == "watchdog_log_verified"]
    accepted = [r for r in verified if r["decision"]["action"] == "fallback_dispatch_accepted"]
    return {"schema": "FOUR_MODE_WATCHDOG_DECISION_EVIDENCE_V1",
            "watchdog_runs_checked": len(decisions),
            "decisions_verified": len(verified),
            "fallback_dispatchs_accepted": len(accepted),
            "accepted_run_ids": [r["run_id"] for r in accepted],
            "capture_trigger_attribution_proven": False,
            "remote_publication_proven": False,
            "note": "A watchdog dispatch acceptance is not proof that a particular capture run originated from it.",
            "runs": decisions}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--history", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    history = json.loads(Path(args.history).read_text(encoding="utf-8"))
    result = inspect(history, args.repo, os.environ.get("GITHUB_TOKEN"))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_WATCHDOG_DECISIONS=" + json.dumps({
        "watchdog_runs_checked": result["watchdog_runs_checked"],
        "decisions_verified": result["decisions_verified"],
        "fallback_dispatchs_accepted": result["fallback_dispatchs_accepted"],
        "accepted_run_ids": result["accepted_run_ids"],
        "runs": [{"run_id": r["run_id"], "evidence_status": r["evidence_status"],
                  "action": (r["decision"] or {}).get("action")}
                 for r in result["runs"]]}, sort_keys=True))


if __name__ == "__main__":
    main()
