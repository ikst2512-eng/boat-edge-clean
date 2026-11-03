"""Check publication evidence without treating an empty capture as an error."""
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path



def verify_future_third_rate(root, publication, observation):
    """A Nov-4+ publication is not fully audited without durable third-rate bytes.

    The branch writer already verifies the original Git first-add provenance.
    This final gate independently checks its output digest and race roster.
    It is a same-job integrity check, not formal independent first receipt.
    """
    evidence = Path(root) / "four-mode-evidence"
    observed = observation["records"]
    future_codes = {row["race_code"] for row in observed
                    if row["race_code"][:8] >= "20261104"}
    # A shadow must use the exact T-12 cutoff independently recorded for
    # that same remote-observed race. Separately self-consistent timestamps
    # are insufficient when the two producers disagree on the deadline.
    observed_cutoffs = {row["race_code"]: row["deadline_minus_12_jst"]
                        for row in observed if row["race_code"] in future_codes}
    if not future_codes:
        return
    original = (evidence / "third-rate-shadow.json").read_bytes()
    shadow = json.loads(original)
    durable = json.loads((evidence / "third-rate-ledger.json").read_text(
        encoding="utf-8"))
    if (not isinstance(shadow, dict)
            or shadow.get("schema") != "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1"
            or shadow.get("status") != "captured_local_after_push_not_remote_proven"
            or shadow.get("formal") is not False
            or shadow.get("publication_commit_sha") != publication["commit_sha"]
            or shadow.get("published_forecasts") != publication["added_forecasts"]
            or type(shadow.get("frozen_before_t_minus_12")) is not int
            or shadow["frozen_before_t_minus_12"] < 1
            or shadow.get("validation_error_count", 0) != 0
            or type(shadow.get("records")) is not list
            or len(shadow["records"]) != publication["added_forecasts"]):
        raise ValueError("future_third_rate_shadow_missing_or_invalid")
    codes = set()
    frozen = 0
    for row in shadow["records"]:
        if not isinstance(row, dict) or not isinstance(row.get("race_code"), str):
            raise ValueError("future_third_rate_roster_invalid")
        code = row["race_code"]
        if code in codes or code not in future_codes:
            raise ValueError("future_third_rate_roster_invalid")
        codes.add(code)
        if row.get("status") == "frozen_in_same_job_before_t_minus_12":
            frozen += 1
            if row.get("source_commit_sha") != publication["commit_sha"]:
                raise ValueError("future_third_rate_commit_mismatch")
            at = datetime.fromisoformat(row["frozen_at_utc"])
            cutoff = datetime.fromisoformat(row["t_minus_12_jst"])
            if (at.utcoffset() is None or cutoff.utcoffset() != timedelta(hours=9)
                    or at >= cutoff):
                raise ValueError("future_third_rate_frozen_after_cutoff")
            try:
                independently_observed_cutoff = datetime.fromisoformat(
                    observed_cutoffs[code])
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                raise ValueError("future_third_rate_remote_cutoff_invalid") from exc
            if (independently_observed_cutoff.utcoffset() != timedelta(hours=9)
                    or cutoff != independently_observed_cutoff):
                raise ValueError("future_third_rate_remote_cutoff_mismatch")
        elif row.get("status") != "ineligible":
            raise ValueError("future_third_rate_unexpected_status")
    if codes != future_codes or frozen != shadow["frozen_before_t_minus_12"]:
        raise ValueError("future_third_rate_frozen_count_mismatch")
    # Every remotely observed pre-T-12 published forecast must have its
    # corresponding frozen third-rate comparison. A single valid shadow
    # cannot certify the completeness of a multi-race publication batch.
    # The append-only writer still retains any valid siblings for research.
    if frozen != len(future_codes):
        raise ValueError("future_third_rate_partial_frozen_roster")
    expected_day = next(iter(future_codes))[:8]
    if (any(code[:8] != expected_day for code in future_codes)
            or durable.get("stored") is not True
            or durable.get("formal") is not False
            or durable.get("status") not in
               ("new_immutable_ledger_entry", "already_preserved_identical")
            or durable.get("branch") != "v2-third-rate-evidence-ledger"
            or durable.get("original_sha256") != hashlib.sha256(original).hexdigest()
            or not isinstance(durable.get("path"), str)
            or not re.fullmatch(
                r"third_rate/" + expected_day +
                r"/run-[1-9][0-9]*-attempt-[1-9][0-9]*[.]json",
                durable["path"])):
        raise ValueError("future_third_rate_not_durable")


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
    # Both branch ledger receipts must come from the exact same capture
    # execution and attempt. Matching SHA256 alone does not bind a pair of
    # independently archived evidence objects to one original job.
    first = re.fullmatch(
        r"github_server/20[0-9]{6}/run-([1-9][0-9]*)-attempt-([1-9][0-9]*)[.]json",
        ledger["path"])
    if not first:
        raise ValueError("github_observation_ledger_run_identity_invalid")
    if any(code[:8] >= "20261104" for code in codes):
        third = read("third-rate-ledger.json")
        path = third.get("path") if type(third) is dict else None
        second = re.fullmatch(
            r"third_rate/20[0-9]{6}/run-([1-9][0-9]*)-attempt-([1-9][0-9]*)[.]json",
            path) if type(path) is str else None
        if not second or first.groups() != second.groups():
            raise ValueError("future_evidence_ledger_run_identity_mismatch")
    verify_future_third_rate(root, publication, observation)
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
