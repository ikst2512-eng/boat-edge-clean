"""Fail-closed same-race historical T-12 proof chain, no cross-race stitching.

Consumes three independently produced, real-original evidence reports:
(1) pinned Nov 3 complete-filenames but incomplete exhibitions,
(2) Nov 9 two-original complete source replay vs immutable frozen forecasts,
(3) independent Nov 9 GitHub source-artifact publication chronology.

A component observed on a different race or date can NEVER fill a missing
component. This report cannot authorize live forecasting or formal accuracy.
"""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

NOV03 = "202611030112"
NOV09 = ("202611091110", "202611091710")
TRIPLE_SHA = "d0ed89f146dff117021c2bc042b20259d6715515"
SCHEMA = "T12_SAME_RACE_INDEPENDENT_PROOF_CHAIN_V1"
MISSING_NOV03 = {
    "exhibition_six_courses",
    "exhibition_times_six",
    "tilt_six",
    "start_exhibition_six",
}


def _jst(value, race):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    try:
        when = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if when.utcoffset() != timedelta(hours=9) or when.strftime("%Y%m%d") != race[:8]:
        raise ValueError("cross-race day or non-JST timestamp")
    return when


def _nonformal(report):
    if (not isinstance(report, dict)
            or report.get("formal") is not False
            or report.get("t12_eligible") is not False
            or report.get("accuracy_scoring_allowed") is not False
            or report.get("new_formal_certifications") != 0
            or report.get("formal_accuracy_denominator") is not None):
        raise ValueError("upstream evidence illegally claims formal accuracy")


def compose(nov3, nov9, remote):
    _nonformal(nov3)
    _nonformal(nov9)
    _nonformal(remote)
    if (nov3.get("schema") != "T12_PINNED_GITHUB_THREE_ORIGINAL_REPLAY_V1"
            or nov3.get("race_code") != NOV03
            or nov3.get("source_git_commit_sha") != TRIPLE_SHA
            or nov3.get("source_git_blob_and_manifest_hashes_reaudited") is not True
            or nov3.get("three_official_original_files_present") is not True
            or nov3.get("source_received_by_t12") is not True
            or nov3.get("six_registration_and_exhibition_components_complete") is not False
            or nov3.get("source_research_components_complete") is not False
            or nov3.get("qualified_three_source_candidates") != 0
            or set(nov3.get("missing_source_components") or []) != MISSING_NOV03
            or len(nov3["missing_source_components"]) != 4
            or nov3.get("model_original_bytes_consumption_independently_verified") is not False
            or nov3.get("independent_first_forecast_git_remote_acceptance_verified") is not False
            or nov3.get("final_entry_independently_verified") is not False):
        raise ValueError("Nov3 fixed immutable three-original replay not credible")
    before = _jst(nov3.get("last_original_received_jst"), NOV03)
    cutoff = _jst(nov3.get("source_cutoff_jst"), NOV03)
    if before > cutoff:
        raise ValueError("Nov3 sources late")
    if (nov9.get("schema") != "T12_NOV09_REAL_OFFICIAL_PAIR_VS_FROZEN_FORECAST_V1"
            or nov9.get("extracted_official_source_originals_replayed") is not True
            or nov9.get("source_run_id") != 42567310743
            or nov9.get("source_artifact_id") != 13652131213
            or nov9.get("two_original_complete_races") != 2
            or nov9.get("matched_pinned_forecasts") != 4
            or nov9.get("matched_forecasts_generated_after_sources") != 0
            or nov9.get("three_official_original_races") != 0
            or nov9.get("independent_model_input_consumption_verified") is not False
            or nov9.get("independent_first_remote_receipt_verified") is not False
            or nov9.get("final_race_entry_verified") is not False):
        raise ValueError("Nov9 two-original source-and-forecast replay not credible")
    if (remote.get("schema") != "T12_SOURCE_ARCHIVE_SERVER_TIME_AUDIT_V1"
            or remote.get("source_run_id") != nov9["source_run_id"]
            or remote.get("source_artifact_id") != nov9["source_artifact_id"]
            or remote.get("artifact_original_zip_sha256_from_github_metadata") !=
               nov9.get("github_original_artifact_digest_from_metadata")
            or remote.get("individual_official_original_bytes_replayed_by_upstream_audit") is not True
            or remote.get("server_timestamp_artifact_archive_before_t12_races") != 2
            or remote.get("source_artifact_server_time_not_first_forecast_git_receipt") is not True
            or remote.get("official_three_originals_replayed") != 0
            or remote.get("post_official_source_frozen_forecasts") != 0):
        raise ValueError("Nov9 archive publication time not linked to original replay")

    n9 = nov9.get("race_rows")
    remotely_archived = remote.get("race_rows")
    if (not isinstance(n9, list) or not isinstance(remotely_archived, list)
            or len(n9) != 2 or len(remotely_archived) != 2):
        raise ValueError("expected exactly two same-race Nov9 reports")
    source_codes = [row.get("race_code") if isinstance(row, dict) else None for row in n9]
    remote_codes = [row.get("race_code") if isinstance(row, dict) else None for row in remotely_archived]
    if sorted(source_codes) != list(NOV09) or sorted(remote_codes) != list(NOV09):
        raise ValueError("mixed or duplicated source/remote race IDs")
    index = {x["race_code"]: x for x in remotely_archived}
    out = [{
        "race_code": NOV03,
        "day_jst": "20261103",
        "official_racelist_original": True,
        "official_beforeinfo_original": True,
        "official_odds_original": True,
        "six_boat_exhibition_complete": False,
        "official_t12_source_cutoff_met": True,
        "independent_source_archive_server_publication_by_t12": False,
        "same_race_three_source_readiness": False,
        "frozen_forecast_generated_after_all_originals": False,
        "actual_model_input_consumption_verified": False,
        "independent_first_forecast_git_remote_receipt_verified": False,
        "final_race_entry_verified": False,
        "source_evidence": "pinned_git_three_originals_20261103",
        "missing_requirements": sorted(MISSING_NOV03) + [
            "independent_source_archive_server_time_not_proven",
            "no_post_source_immutable_forecast",
            "model_input_original_consumption_unverified",
            "first_forecast_remote_acceptance_unverified",
            "final_race_entry_unverified",
        ],
        "formal": False,
    }]
    for row in sorted(n9, key=lambda x: x["race_code"]):
        code = row["race_code"]
        archive = index[code]
        last = _jst(row.get("official_latest_original_received_jst"), code)
        limit = _jst(row.get("official_t12_cutoff_jst"), code)
        archived_limit = _jst(archive.get("official_t12_cutoff_jst"), code)
        archived_last = _jst(
            archive.get("last_official_original_receipt_self_recorded_jst"), code)
        if (last > limit or last != archived_last or limit != archived_limit
                or row.get("official_pair_originals_replayed_complete") is not True
                or row.get("racelist_official_original_present") is not False
                or row.get("formal") is not False
                or row.get("accuracy_scoring_allowed") is not False
                or archive.get("two_official_original_bytes_replayed") is not True
                or archive.get("third_official_racelist_original_replayed") is not False
                or archive.get("github_artifact_updated_before_t12_one_sec_margin") is not True
                or archive.get("forecast_generated_after_all_official_sources") is not False
                or archive.get("independent_first_forecast_git_remote_receipt_proven") is not False
                or archive.get("formal") is not False):
            raise ValueError("Nov9 same-race original/remote-time integrity mismatch")
        modes = row.get("forecasts")
        if (not isinstance(modes, dict)
                or set(modes) != {"clean", "v2_four_mode"}
                or any(not isinstance(p, dict)
                       or p.get("generated_strictly_after_official_pair") is not False
                       or p.get("independent_actual_model_original_consumption_verified") is not False
                       or p.get("first_git_remote_receipt_verified") is not False
                       or p.get("formal") is not False
                       for p in modes.values())):
            raise ValueError("Nov9 frozen forecast timing or lineage unresolved")
        out.append({
            "race_code": code,
            "day_jst": code[:8],
            "official_racelist_original": False,
            "official_beforeinfo_original": True,
            "official_odds_original": True,
            "six_boat_exhibition_complete": True,
            "official_t12_source_cutoff_met": True,
            "independent_source_archive_server_publication_by_t12": True,
            "same_race_three_source_readiness": False,
            "frozen_forecast_generated_after_all_originals": False,
            "actual_model_input_consumption_verified": False,
            "independent_first_forecast_git_remote_receipt_verified": False,
            "final_race_entry_verified": False,
            "source_evidence": "nov09_github_actions_pair_and_remote_archive",
            "missing_requirements": [
                "third_official_racelist_original_not_replayed_same_race",
                "no_post_source_immutable_forecast",
                "model_input_original_consumption_unverified",
                "first_forecast_remote_acceptance_unverified",
                "final_race_entry_unverified",
            ],
            "formal": False,
        })
    if len({r["race_code"] for r in out}) != 3:
        raise ValueError("cross-race source identity collision")
    if any(r["same_race_three_source_readiness"] for r in out):
        raise ValueError("unsupported formal candidate")
    # These are observed coverage counts for the three *fixed historical*
    # races, not an independent prospective performance denominator.
    # Reuse source-replayed per-race booleans; never upgrade an old forecast.
    five_gate_keys = (
        "official_beforeinfo_six_exhibition",
        "official_odds_120",
        "official_deadline_source_cutoff",
        "forecast_after_official_sources_before_t12",
        "independent_first_forecast_git_acceptance",
    )
    five_gate_rows = []
    for race in out:
        checks = {
            "official_beforeinfo_six_exhibition": (
                race["official_beforeinfo_original"] is True
                and race["six_boat_exhibition_complete"] is True),
            "official_odds_120": race["official_odds_original"] is True,
            "official_deadline_source_cutoff": (
                race["official_t12_source_cutoff_met"] is True),
            "forecast_after_official_sources_before_t12": (
                race["frozen_forecast_generated_after_all_originals"] is True),
            "independent_first_forecast_git_acceptance": (
                race["independent_first_forecast_git_remote_receipt_verified"] is True),
        }
        # The local HTTP receipt claimed by the collector is NOT the same
        # proof as independent GitHub source ZIP publication. Neither is the
        # FIRST remote acceptance of the frozen forecast in Git history.
        source_published = (
            race["independent_source_archive_server_publication_by_t12"] is True)
        if checks["official_beforeinfo_six_exhibition"] is False:
            next_blocker = "complete_six_boat_exhibition_missing"
        elif race["official_racelist_original"] is not True:
            next_blocker = "same_race_official_racelist_missing"
        elif source_published is False:
            next_blocker = "independent_source_zip_publication_unverified"
        elif checks["forecast_after_official_sources_before_t12"] is False:
            next_blocker = "source_following_forecast_not_generated"
        elif checks["independent_first_forecast_git_acceptance"] is False:
            next_blocker = "first_forecast_git_remote_receipt_unverified"
        else:
            next_blocker = "other_formal_gates_unverified"
        five_gate_rows.append({
            "race_code": race["race_code"],
            "gates": checks,
            "all_five_verified": all(checks.values()),
            "collector_source_receipt_self_reported_before_t12": (
                race["official_t12_source_cutoff_met"] is True),
            "independent_source_zip_published_before_t12": source_published,
            "source_zip_publication_is_first_forecast_git_receipt": False,
            "next_source_or_forecast_blocker": next_blocker,
            "extra_official_racelist_original": race["official_racelist_original"] is True,
            "extra_model_original_consumption": race["actual_model_input_consumption_verified"] is True,
            "extra_final_entry": race["final_race_entry_verified"] is True,
            "formal": False,
        })
    five_gate_counts = {
        key: sum(row["gates"][key] is True for row in five_gate_rows)
        for key in five_gate_keys
    }
    if len(five_gate_rows) != 3 or any(row["all_five_verified"] for row in five_gate_rows):
        raise ValueError("historical cohort cannot be formally certified")
    return {
        "schema": SCHEMA,
        "scope": "three_disjoint_real_historical_source_races_no_cross_race_stitch",
        "races_compared": len(out),
        "historical_five_gate_counts": five_gate_counts,
        "historical_five_gate_by_race": five_gate_rows,
        "historical_all_five_gates_verified": 0,
        "historical_source_time_provenance": {
            "collector_source_receipt_self_reported_before_t12": sum(
                row["collector_source_receipt_self_reported_before_t12"]
                for row in five_gate_rows),
            "independent_source_zip_published_before_t12": sum(
                row["independent_source_zip_published_before_t12"]
                for row in five_gate_rows),
            "first_forecast_git_remote_receipt_verified": sum(
                row["gates"]["independent_first_forecast_git_acceptance"]
                for row in five_gate_rows),
        },
        "historical_first_blocker_counts": {
            stage: sum(row["next_source_or_forecast_blocker"] == stage
                       for row in five_gate_rows)
            for stage in sorted({row["next_source_or_forecast_blocker"]
                                 for row in five_gate_rows})
        },
        "historical_extra_gate_counts": {
            "official_racelist_original": sum(
                row["extra_official_racelist_original"] is True for row in five_gate_rows),
            "actual_model_original_consumption": sum(
                row["extra_model_original_consumption"] is True for row in five_gate_rows),
            "final_entry_verified": sum(
                row["extra_final_entry"] is True for row in five_gate_rows),
        },
        "raw_three_original_sets_present": 1,
        "two_original_sets_with_complete_exhibition_and_120_odds": 2,
        "source_archive_server_published_before_t12_races": 2,
        "fully_qualified_same_race_three_original_t12_sources": 0,
        "forecasts_generated_after_all_originals": 0,
        "formal_accuracy_denominator": None,
        "new_formal_certifications": 0,
        "cross_race_original_combination_allowed": False,
        "races": out,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nov03-three", required=True)
    p.add_argument("--nov09-two", required=True)
    p.add_argument("--nov09-remote", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    args = [json.loads(Path(path).read_text(encoding="utf-8"))
            for path in (a.nov03_three, a.nov09_two, a.nov09_remote)]
    result = compose(*args)
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("T12_SAME_RACE_PROOF_CHAIN=" + json.dumps({
        k: v for k, v in result.items() if k != "races"
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
