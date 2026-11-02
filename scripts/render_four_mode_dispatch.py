"""Independent Render cron wakeup for GitHub's existing safeguarded capture.

Configure GITHUB_DISPATCH_TOKEN as a Render secret with Actions read/write
permission for this repository. Never clone/write forecast archives on Render.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from scripts.four_mode_watchdog_policy import should_dispatch

REPOSITORY = "ikst2512-eng/boat-edge-clean"
WORKFLOW = "four-mode-prospective-capture.yml"

def run(*, token, now=None, request=urllib.request.urlopen):
    if not token:
        raise ValueError("GITHUB_DISPATCH_TOKEN_missing")
    now = now or datetime.now(timezone.utc)
    # Never call GitHub or require API access outside scheduled JST hours.
    from scripts.four_mode_watchdog_policy import JST
    if not 7 <= now.astimezone(JST).hour <= 20:
        return {"action": "no_dispatch", "reason": "outside_capture_hours", "checked_runs": 0}
    base = f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    events = []
    for event in ("schedule", "workflow_dispatch"):
        req = urllib.request.Request(base + "/runs?event=" + event + "&per_page=30", headers=headers)
        with request(req, timeout=20) as response:
            events.extend(json.load(response)["workflow_runs"])
    decision = should_dispatch(events, now, "render_cron")
    if not decision:
        return {"action": "no_dispatch", "checked_runs": len(events)}
    body = json.dumps({"ref": "main"}).encode()
    req = urllib.request.Request(base + "/dispatches", data=body,
                                 headers={**headers, "Content-Type": "application/json"},
                                 method="POST")
    with request(req, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("dispatch_not_accepted")
    return {"action": "dispatch_accepted_not_publication_proof", "checked_runs": len(events)}

if __name__ == "__main__":
    print(json.dumps(run(token=os.environ.get("GITHUB_DISPATCH_TOKEN")), sort_keys=True))
