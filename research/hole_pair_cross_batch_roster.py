"""Read-only cross-run race deduplication for future hole-pair research.

Every supplied artifact must have its own exact payload digest and its
complete immutable-main snapshot ID census. This compares observations, NOT
an independently verified first remote receipt. Never open results, select
tickets, increment formal pilot/confirmation counts or modify storage.
"""
import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from hole_pair_remote_receipt_evidence import canonical_bytes, _validate_frozen
from research.hole_pair_universe_coverage import reconcile

UTC = timezone.utc
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
UTC_TEXT = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z"
)
MAX_BATCHES = 60
SCHEMA = "HOLE_PAIR_CROSS_BATCH_SNAPSHOT_DEDUP_V1"


def utc_date(value):
    if type(value) is not str or not UTC_TEXT.fullmatch(value):
        raise ValueError("untrusted_artifact_upload_clock")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("untrusted_artifact_upload_clock") from exc
    if dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError("untrusted_artifact_upload_clock")
    return dt.astimezone(UTC)


def inspect_observation(observation):
    if type(observation) is not dict or set(observation) != {
            "run_id", "artifact_id", "artifact_observed_at_utc",
            "manifest_sha256", "manifest"}:
        raise ValueError("invalid_artifact_observation")
    run_id, artifact_id = observation["run_id"], observation["artifact_id"]
    if type(run_id) is not int or run_id <= 0 or type(artifact_id) is not int or artifact_id <= 0:
        raise ValueError("invalid_github_run_or_artifact_id")
    observed = utc_date(observation["artifact_observed_at_utc"])
    batch = observation["manifest"]
    if type(batch) is not dict or (type(observation["manifest_sha256"]) is not str
        or not SHA256.fullmatch(observation["manifest_sha256"])
        or hashlib.sha256(canonical_bytes(batch)).hexdigest() != observation["manifest_sha256"]):
        raise ValueError("untrusted_artifact_manifest_digest")
    if batch.get("schema") != "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1" or (
            batch.get("status") != "local_predeadline_freeze_not_formal") or any(
        batch.get(k) is not False for k in (
            "formal", "prospective_validation",
            "independent_first_receipt_verified", "production_forecast_changed")
    ):
        raise ValueError("untrusted_batch_status_or_formal_claim")
    day, main_sha = batch.get("capture_day_jst"), batch.get("source_main_commit")
    codes, records, excluded = (
        batch.get("source_forecast_codes"), batch.get("records"),
        batch.get("excluded_race_codes_by_reason"))
    coverage = reconcile(day, main_sha, codes, records, excluded)
    if (batch.get("source_snapshot_coverage") != coverage
        or batch.get("eligible_forecasts_examined") != coverage["snapshot_forecasts_examined"]
        or batch.get("frozen_count") != coverage["frozen_locally_unverified"]
        or batch.get("excluded_by_reason") != coverage["excluded_by_reason"]):
        raise ValueError("batch_and_source_snapshot_census_mismatch")
    # Never infer 'first' from this self-declared observation timestamp.
    events = []
    for record in records:
        code, cutoff = _validate_frozen(record)
        # An artifact observation cannot chronologically precede the exact
        # local candidate bytes that it purports to contain. This is only an
        # internal inconsistency check, NOT trusted server time attestation.
        finish = datetime.fromisoformat(record["local_finish_jst"]).astimezone(UTC)
        if observed <= finish:
            raise ValueError("artifact_observation_precedes_candidate_calculation")
        events.append({
            "race_code": code, "kind": "frozen",
            "payload_sha256": hashlib.sha256(canonical_bytes(record)).hexdigest(),
            "record": record, "declared_cutoff": cutoff,
        })
    for reason, names in excluded.items():
        for code in names:
            events.append({"race_code": code, "kind": "excluded", "reason": reason})
    return (observed, run_id, artifact_id, events)


def audit(observations):
    if type(observations) is not list or len(observations) > MAX_BATCHES:
        raise ValueError("untrusted_cross_batch_count")
    batches, ids = [], set()
    for ob in observations:
        observed, run, artifact, events = inspect_observation(ob)
        if (run, artifact) in ids:
            raise ValueError("duplicated_run_artifact_observation")
        ids.add((run, artifact))
        batches.append((observed, run, artifact, events))
    batches.sort(key=lambda x: (x[0], x[1], x[2]))
    per_race = defaultdict(list)
    for observed, run, artifact, events in batches:
        for event in events:
            per_race[event["race_code"]].append(
                (observed.isoformat(), run, artifact, event))
    summary = Counter()
    rows = []
    for code in sorted(per_race):
        observations_for_race = per_race[code]
        first = observations_for_race[0][-1]
        # Two sources observed at the same reported instant cannot establish
        # a first disposition from arbitrary run/artifact ID sort order.
        earliest_at = observations_for_race[0][0]
        earliest_dispositions = {
            (row[-1]["kind"], row[-1].get("reason")) for row in observations_for_race
            if row[0] == earliest_at
        }
        ambiguous_first_disposition = len(earliest_dispositions) > 1
        frozen = [x[-1] for x in observations_for_race if x[-1]["kind"] == "frozen"]
        excluded = [x[-1] for x in observations_for_race if x[-1]["kind"] == "excluded"]
        distinct_bytes = {x["payload_sha256"] for x in frozen}
        first_exclusion_upgrade = first["kind"] == "excluded" and bool(frozen)
        conflicting_freeze = len(distinct_bytes) > 1
        if conflicting_freeze or first_exclusion_upgrade or ambiguous_first_disposition:
            state = "quarantined_cross_batch_conflict"
            summary["quarantined_cross_batch_conflict"] += 1
        elif first["kind"] == "frozen":
            state = "unique_local_candidate_not_independently_received"
            summary["unique_local_candidate_not_independently_received"] += 1
        else:
            state = "initially_excluded_not_eligible"
            summary["initially_excluded_not_eligible"] += 1
        # Repeated exact candidate bytes can never add another scored race.
        summary["identical_frozen_repeats"] += max(
            0, len(frozen) - len(distinct_bytes))
        summary["later_exclusion_after_initial_freeze"] += int(
            first["kind"] == "frozen" and bool(excluded))
        rows.append({
            "race_code": code,
            "status": state,
            "earliest_observed_run_id_not_independent_first_receipt": observations_for_race[0][1],
            "earliest_observed_artifact_id_not_independent_first_receipt": observations_for_race[0][2],
            "observations_total": len(observations_for_race),
            "frozen_records_seen": len(frozen),
            "distinct_frozen_record_sha256_count": len(distinct_bytes),
            "excluded_observations_seen": len(excluded),
            "first_observed_classification": first["kind"],
            "first_excluded_then_later_frozen": first_exclusion_upgrade,
            "conflicting_frozen_record": conflicting_freeze,
            "ambiguous_equal_time_first_disposition": ambiguous_first_disposition,
        })
    return {
        "schema": SCHEMA,
        "artifacts_observed": len(batches),
        "distinct_race_codes": len(rows),
        "race_observations_total": sum(row["observations_total"] for row in rows),
        "unique_frozen_unverified": summary["unique_local_candidate_not_independently_received"],
        "initially_excluded": summary["initially_excluded_not_eligible"],
        "quarantined_conflicts": summary["quarantined_cross_batch_conflict"],
        "identical_frozen_repeats_not_added_to_denominator": summary["identical_frozen_repeats"],
        "late_exclusions_after_first_frozen_reference": summary["later_exclusion_after_initial_freeze"],
        "event_roster_reconciliation_passed": True,
        "artifact_observation_time_independently_attested": False,
        "official_day_schedule_coverage_verified": False,
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "formally_eligible": 0,
        "pilot_formally_eligible": 0,
        "confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "rows": rows,
        "warning": (
            "Only exact repeated bytes are collapsed in this read-only research view. "
            "Conflicting candidate revisions or upgrades after an earlier exclusion "
            "are quarantined. Artifact creation/observation times and source snapshot "
            "universe are not independently signed first receipts or official T-12 proof."
        ),
    }
