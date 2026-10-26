"""Read-only online GitHub evidence fetch; never opens outcomes or authorizes scoring."""
import argparse
import json
import urllib.request
from github_receipt_verify import verify

API = "https://api.github.com"
REPO = "ikst2512-eng/boat-edge-clean"

def fetch_github(relative_path):
    if not relative_path.startswith("/repos/" + REPO + "/"):
        raise ValueError("unapproved GitHub API route")
    if not any(relative_path.startswith("/repos/" + REPO + "/"+prefix) for prefix in ("git/commits/", "git/trees/", "git/blobs/", "actions/runs/")):\n        raise ValueError("unapproved evidence endpoint")\n    request = urllib.request.Request(
        API + relative_path,
        headers={"Accept":"application/vnd.github+json",
                 "User-Agent":"boat-edge-clean-research-receipt-audit"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)

def audit_live(*, branch, commit, path, expected_sha256, official_deadline, run_id):
    report = verify(fetch_github, repo=REPO, branch=branch, commit=commit,
                    path=path, expected_sha256=expected_sha256,
                    official_deadline=official_deadline, run_id=run_id)
    # This entrypoint NEVER treats remote receipt evidence as scoring permission.
    if report.get("ready_for_scoring") is not False:
        raise ValueError("unsafe verifier report")
    return report

def main():
    parser=argparse.ArgumentParser(description="Research-only GitHub first-seen receipt audit")
    parser.add_argument("--branch",required=True)
    parser.add_argument("--commit",required=True)
    parser.add_argument("--path",required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--official-deadline",required=True)
    parser.add_argument("--run-id",type=int,required=True)
    args=parser.parse_args()
    print(json.dumps(audit_live(branch=args.branch,commit=args.commit,
          path=args.path,expected_sha256=args.sha256,
          official_deadline=args.official_deadline,run_id=args.run_id),
          ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
