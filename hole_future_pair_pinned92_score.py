"""Score ONLY the pre-frozen Nov 6 92-race pair-policy research artifact.

Data never comes from re-selecting archived forecasts after outcomes appear.
The exact pre-result artifact JSON bytes are SHA256 pinned. Candidate replay,
confirmed-result trust and selector-version gates come from #1685 review().
This report is explicitly nonformal: GitHub artifact time is not independent
first-receipt attestation and official T-12 completeness is separate.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE_JSON_SHA256 = "722540fbae1e8160be41d762e0e6bd9bf9345df4762a50d8320571311973e3d2"
SOURCE_MAIN_COMMIT = "b3c87901b8115ea2fa22992e3402945e34a517ae"
ARTIFACT_ID = 13475051686
ARTIFACT_CREATED_UTC = datetime(2026, 11, 6, 3, 25, 25, tzinfo=timezone.utc)
EXPECTED_COUNT = 92
METHOD_SHA256 = "ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb"
POLICIES = ("baseline", "same_pair_two_thirds", "two_pairs_one_third")
# BOAT RACE official Nov 6 calendar: Tokoname (venue 08) was cancelled/postponed.
# Only the seven venue-08 races contained in the immutable 92-record batch.
OFFICIAL_CANCELLED_CODES = frozenset(f"2026110608{i:02d}" for i in range(6, 13))
OFFICIAL_CANCELLED_SOURCE = "https://www.boatrace.jp/owpc/pc/race/index?hd=20261106"
TOPS = (1, 3, 5, 10)
JST = timezone(timedelta(hours=9))
CODE = re.compile(r"20261106\d{4}\Z")


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _pair(ticket):
    parts = ticket.split("-")
    if len(parts) != 3 or len(set(parts)) != 3 or set(parts) - set("123456"):
        raise ValueError("invalid_ticket")
    return tuple(parts[:2])


def score(frozen_file, root, reviewer, *, expected_digest=SOURCE_JSON_SHA256,
          expected_count=EXPECTED_COUNT, artifact_created=ARTIFACT_CREATED_UTC):
    """Read-only, fail-closed, aligned comparison; reviewer is #1685 review()."""
    frozen_file = Path(frozen_file)
    root = Path(root)
    if frozen_file.is_symlink() or not frozen_file.is_file() or frozen_file.stat().st_size > 5_000_000:
        raise ValueError("frozen_artifact_unavailable_or_unsafe")
    raw = frozen_file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("pre_result_artifact_digest_mismatch")
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get("schema") != "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1"
            or data.get("status") != "local_predeadline_freeze_not_formal"
            or data.get("source_main_commit") != SOURCE_MAIN_COMMIT
            or data.get("capture_day_jst") != "20261106"
            or data.get("frozen_count") != expected_count
            or type(data.get("eligible_forecasts_examined")) is not int
            or data["eligible_forecasts_examined"] != 130
            or data.get("excluded_by_reason") != {"after_t_minus_12": 38}
            or not isinstance(data.get("records"), list)
            or len(data["records"]) != expected_count
            or any(data.get(k) is not False for k in (
                "formal", "prospective_validation", "independent_first_receipt_verified",
                "production_forecast_changed"))):
        raise ValueError("untrusted_frozen_batch_header")
    if artifact_created.utcoffset() is None:
        raise ValueError("untrusted_artifact_clock")
    seen = set()
    # Verify every frozen candidate and T-12 server-artifact boundary before
    # opening even one race result. A malformed cohort must not be partly scored.
    for record in data["records"]:
        if not isinstance(record, dict):
            raise ValueError("untrusted_record")
        code = record.get("race_code")
        if not isinstance(code, str) or not CODE.fullmatch(code) or code in seen:
            raise ValueError("invalid_or_duplicate_race_code")
        seen.add(code)
        if (record.get("schema") != "HOLE_PAIR_FUTURE_FREEZE_V1"
                or record.get("status") != "locally_frozen_unverified"
                or record.get("method_source_sha256") != METHOD_SHA256
                or any(record.get(k) is not False for k in (
                    "formal", "prospective_validation", "independent_first_receipt_verified",
                    "production_forecast_changed"))):
            raise ValueError("invalid_record_claim_or_method")
        try:
            cutoff = datetime.fromisoformat(record["t_minus_12_jst"])
            start = datetime.fromisoformat(record["local_start_jst"])
            finish = datetime.fromisoformat(record["local_finish_jst"])
            deadline = datetime.fromisoformat(record["deadline_jst"])
            choices = record["candidates"]
            baseline = choices["baseline"]
            if (cutoff.utcoffset() != timedelta(hours=9)
                    or start.utcoffset() != timedelta(hours=9)
                    or finish.utcoffset() != timedelta(hours=9)
                    or cutoff != deadline - timedelta(minutes=12)
                    or not (artifact_created < cutoff and start <= finish < cutoff)):
                raise ValueError("unverified_pre_cutoff_clock")
            if (not isinstance(choices, dict) or set(choices) != set(POLICIES)
                    or not isinstance(baseline, list) or len(baseline) != 10
                    or len(set(baseline)) != 10
                    or _digest(choices) != record["candidates_sha256"]):
                raise ValueError("invalid_candidate_digest_or_budget")
            old_pairs = {_pair(t) for t in baseline}
            for mode in POLICIES:
                picked = choices[mode]
                if (not isinstance(picked, list) or len(picked) != 10
                        or len(set(picked)) != 10 or not all(_pair(t) for t in picked)
                        or picked[:5] != baseline[:5]
                        or not old_pairs.issubset({_pair(t) for t in picked})):
                    raise ValueError("top5_pair_or_budget_violation")
        except (KeyError, TypeError, ValueError, AssertionError, AttributeError) as exc:
            raise ValueError("invalid_frozen_candidate_or_timing:" + code) from exc
    hits = {mode: {f"top{k}": 0 for k in TOPS} for mode in POLICIES}
    gained = {mode: {f"top{k}": 0 for k in TOPS} for mode in POLICIES[1:]}
    lost = {mode: {f"top{k}": 0 for k in TOPS} for mode in POLICIES[1:]}
    dispositions = Counter()
    rows = []
    for record in data["records"]:
        code = record["race_code"]
        source = root / "four_mode_forecasts" / (code + ".json")
        if source.is_symlink() or not source.is_file() or source.stat().st_size > 30000:
            dispositions["source_file_unavailable_or_unsafe"] += 1
            continue
        blob = source.read_bytes()
        git_blob = hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest()
        if (hashlib.sha256(blob).hexdigest() != record.get("source_sha256")
                or git_blob != record.get("source_git_blob_sha1")):
            dispositions["source_fingerprint_mismatch"] += 1
            continue
        # Officially cancelled races have no winning trifecta. Never label them
        # pending, count them as misses, or look up a replacement-day result.
        if code in OFFICIAL_CANCELLED_CODES:
            if (root / "confirmed_results" / (code + ".json")).exists():
                raise ValueError("cancelled_race_has_result_file:" + code)
            dispositions["officially_cancelled_no_result"] += 1
            continue
        verdict = reviewer(record, root)
        status = verdict.get("status") if isinstance(verdict, dict) else None
        if status == "result_not_yet_confirmed":
            # The reviewer groups absent and invalid confirmed results together.
            # A present but unusable file must fail closed, not silently vanish
            # from the scored denominator as an ordinary pending race.
            result_path = root / "confirmed_results" / (code + ".json")
            if result_path.exists() or result_path.is_symlink():
                raise ValueError("saved_result_exists_but_untrusted:" + code)
            dispositions["pending_independent_result"] += 1
            continue
        if status != "reference_scored_without_independent_receipt" or verdict.get("comparable") != 1:
            dispositions["review_rejected_" + str(status)] += 1
            continue
        flags = verdict.get("flags")
        ranks = verdict.get("ranks")
        if not isinstance(flags, dict) or set(flags) != set(POLICIES) or not isinstance(ranks, dict):
            raise ValueError("invalid_review_flags:" + code)
        for mode in POLICIES:
            if mode not in ranks or type(ranks[mode]) is not int or not 0 <= ranks[mode] <= 10:
                raise ValueError("invalid_review_rank:" + code)
            for k in TOPS:
                f = f"top{k}"
                expected = 0 < ranks[mode] <= k
                if (type(flags[mode].get(f)) is not bool or flags[mode][f] != expected):
                    raise ValueError("invalid_review_flag:" + code)
                hits[mode][f] += int(expected)
                if mode != "baseline":
                    gained[mode][f] += int(expected and not flags["baseline"][f])
                    lost[mode][f] += int(flags["baseline"][f] and not expected)
        rows.append({"race_code": code, "ranks": ranks, "flags": flags})
        dispositions["scored_nonformal"] += 1
    for mode in POLICIES[1:]:
        for k in TOPS:
            f = f"top{k}"
            if hits[mode][f] - hits["baseline"][f] != gained[mode][f] - lost[mode][f]:
                raise ValueError("paired_comparison_mismatch")
            if k in (1, 3, 5) and (gained[mode][f] or lost[mode][f]):
                raise ValueError("protected_top5_outcome_changed")
    if sum(dispositions.values()) != expected_count or len(rows) != dispositions["scored_nonformal"]:
        raise ValueError("denominator_mismatch")
    return {"schema": "HOLE_PAIR_PINNED_92_NONFORMAL_SCORE_V1",
            "status": "partly_scored_nonformal" if rows else "no_results_for_pinned_candidates",
            "frozen_artifact_id": ARTIFACT_ID,
            "source_manifest_sha256": expected_digest,
            "artifact_created_at_utc": artifact_created.isoformat(),
            "frozen": expected_count,
            "scored_nonformal": len(rows), "dispositions": dict(sorted(dispositions.items())),
            "officially_cancelled_codes": sorted(OFFICIAL_CANCELLED_CODES & seen),
            "official_cancellation_source": OFFICIAL_CANCELLED_SOURCE,
            "hits": hits, "gained": gained, "lost": lost, "rows": rows,
            "formal": False, "prospective_validation": False,
            "independent_first_receipt_verified": False,
            "production_forecast_changed": False,
            "warning": "Pre-result pinned exact 92-candidate artifact; local clocks and GitHub artifact creation do NOT certify independent first external receipt or official T-12 completeness. Officially cancelled races are excluded from the scored denominator; other missing results are pending, never misses."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", required=True, help="Extracted research_candidate_freeze.json from artifact 13475051686")
    parser.add_argument("--root", default=".", help="Main checkout with original forecasts and independent results")
    args = parser.parse_args()
    from hole_future_pair_precommit import review
    print(json.dumps(score(args.frozen, args.root, review), ensure_ascii=False,
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
