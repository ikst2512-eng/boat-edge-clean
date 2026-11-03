"""Check publication evidence without treating an empty capture as an error."""
import json
from pathlib import Path


def verify(root):
    root = Path(root)
    evidence = root / "four-mode-evidence"
    def read(name):
        return json.loads((evidence / name).read_text(encoding="utf-8"))
    publication = read("publication.json")
    outcome = publication.get("outcome")
    if outcome == "no_eligible_candidates":
        return {"status": "no_new_forecasts", "evidence_required": False}
    if outcome != "pushed_to_main":
        raise ValueError("publication_not_confirmed")
    count = publication.get("added_forecasts")
    if type(count) is not int or count < 1:
        raise ValueError("invalid_published_count")
    observation = read("github-server-observation.json")
    ledger = read("github-server-observation-ledger.json")
    if (observation.get("status") != "remote_observation_audited_nonformal"
            or observation.get("publication_commit_sha") != publication.get("commit_sha")
            or observation.get("publication_count") != count
            or len(observation.get("records", [])) != count
            or observation.get("unverified_count") != 0
            or observation.get("observed_before_t_minus_12") != count
            or ledger.get("stored") is not True
            or ledger.get("status") not in (
                "new_append_only_observation", "already_preserved_identical")
            or ledger.get("formal") is not False):
        raise ValueError("published_observation_not_durable_and_early")
    return {"status": "published_with_durable_early_observation",
            "evidence_required": True, "published": count}


if __name__ == "__main__":
    try:
        print("FOUR_MODE_EVIDENCE_VERDICT=" + json.dumps(verify("."), sort_keys=True))
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("::error::Published forecast evidence verification failed: "
              + type(exc).__name__)
        raise SystemExit(2)
