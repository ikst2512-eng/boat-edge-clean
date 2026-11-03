"""Check publication evidence without treating an empty capture as an error."""
import json
import hashlib
import re
from datetime import datetime, timedelta
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
    observation_path = evidence / "github-server-observation.json"
    observation_bytes = observation_path.read_bytes()
    observation = json.loads(observation_bytes)
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
            or ledger.get("formal") is not False
            or ledger.get("sha256") != hashlib.sha256(observation_bytes).hexdigest()
            or not isinstance(ledger.get("path"), str)
            or not re.fullmatch(r"github_server/20[0-9]{6}/run-[1-9][0-9]*-attempt-[1-9][0-9]*\.json",
                                ledger["path"])):
        raise ValueError("published_observation_not_durable_and_early")
    # An aggregate count does not prove every race was observed before T-12.
    # The append-only ledger has already read back this exact evidence hash;
    # revalidate its full early-only roster at the final capture gate.
    sha = publication.get("commit_sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("invalid_published_sha")
    codes = set()
    records = observation["records"]
    if not isinstance(records, list):
        raise ValueError("invalid_observation_rows")
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("invalid_observation_row")
        code = row.get("race_code")
        if (not isinstance(code, str)
                or not re.fullmatch(r"20[0-9]{10}", code)
                or code in codes
                or row.get("first_add_commit") != sha
                or row.get("status") != "github_server_observed_before_t_minus_12"
                or row.get("first_add_blob_matches_remote") is not True):
            raise ValueError("invalid_observation_row")
        codes.add(code)
        try:
            event = datetime.fromisoformat(row["github_api_server_date_utc"].replace("Z", "+00:00"))
            cutoff = datetime.fromisoformat(row["deadline_minus_12_jst"])
            if (event.utcoffset() != timedelta(0)
                    or cutoff.utcoffset() != timedelta(hours=9)
                    or cutoff.strftime("%Y%m%d") != code[:8]
                    or event >= cutoff):
                raise ValueError("observation_not_before_t_minus_12")
        except (KeyError, AttributeError, TypeError, OverflowError) as exc:
            raise ValueError("invalid_observation_timestamp") from exc
    if len(codes) != count or observation.get("observed_after_t_minus_12") != 0:
        raise ValueError("observation_race_count_mismatch")
    return {"status": "published_with_durable_early_observation",
            "evidence_required": True, "published": count}


def record_verdict(root):
    """Persist both successful and failed final gates for next-day audits."""
    root = Path(root)
    target = root / "four-mode-evidence" / "final-evidence-verdict.json"
    try:
        result = verify(root)
        verdict = {"schema": "FOUR_MODE_FINAL_EVIDENCE_VERDICT_V1",
                   "status": "passed", "detail": result}
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        verdict = {"schema": "FOUR_MODE_FINAL_EVIDENCE_VERDICT_V1",
                   "status": "failed", "error_type": type(exc).__name__}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(verdict, sort_keys=True) + "\n", encoding="utf-8")
    return verdict


if __name__ == "__main__":
    verdict = record_verdict(".")
    print("FOUR_MODE_EVIDENCE_VERDICT=" + json.dumps(verdict, sort_keys=True))
    if verdict["status"] == "failed":
        print("::error::Published forecast evidence verification failed: "
              + verdict["error_type"])
        raise SystemExit(2)
