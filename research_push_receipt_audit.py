"""Research-only publication gate for independently logged GitHub push events.

GitHub Actions push-run created_at is server-provided and later than the push
event. A matching head SHA and created_at strictly before cutoff provide
conservative evidence of remote presence before cutoff. Commit author/committer
timestamps alone are not accepted. No model is validated by this check.
"""
from datetime import datetime

def audit_push_receipt(pair, run, published_sha):
    cutoff=datetime.fromisoformat(pair["cutoff_jst"])
    frozen=datetime.fromisoformat(pair["frozen_at_jst"])
    created=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
    if any(t.tzinfo is None or t.utcoffset() is None for t in (cutoff,frozen,created)):
        raise ValueError("timestamps need timezone")
    matched=(run.get("event")=="push" and run.get("head_sha")==published_sha
             and len(published_sha)==40 and run.get("repository",{}).get("full_name")
             =="ikst2512-eng/boat-edge-clean"
             and run.get("head_branch")=="research/paired-hit-evaluation-20261027")
    before=frozen <= created < cutoff
    return {"race_code":pair["race_code"],"server_observed_pre_cutoff":bool(matched and before),
            "run_id":run.get("id"),"created_at":created.isoformat(),
            "commit_sha":published_sha,"warning":"Requires verifying pair blob belongs to matching commit; an Actions run alone cannot establish contents."}
