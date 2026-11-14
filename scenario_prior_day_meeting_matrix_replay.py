"""Retrospective prior-day form -> 120 scenario covariates; never a forecast.

This is a NONFITTED research-only projection of the official same-race
historical raw+shadow bundle. Read-only replay AFTER the target is over is
not a prospectively written candidate. The adapter does not infer unobserved
wall/escape-assist, motor count or deciding method from finishes.
"""
from datetime import datetime, timedelta
import re

from scenario_attack_benefit_feature_matrix import build_attack_benefit_matrix

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REG = re.compile(r"[0-9]{4}\Z")


def replay_prior_day_form_into_unfitted_matrix(meeting, manifest, shadow, cutoff_jst):
    if (type(meeting) is not dict
            or meeting.get("schema") != "OFFICIAL_RACELIST_PRIOR_DAY_MEETING_FORM_RESEARCH_V1"
            or type(manifest) is not dict
            or manifest.get("schema") != "OFFICIAL_REAUDITED_INPUT_MANIFEST_V1"
            or type(shadow) is not dict
            or shadow.get("research_only") is not True
            or shadow.get("formal_t12_certified") is not False
            or shadow.get("model_accuracy_verified") is not False
            or shadow.get("generated") is not True
            or manifest.get("official_source_fields_reconstructed") is not True
            or manifest.get("formal_t12_certified") is not False
            or meeting.get("only_prior_day_settled_results") is not True
            or meeting.get("winning_method_from_result_not_inferred") is not True
            or meeting.get("source_receipt_independently_attested") is not False
            or meeting.get("same_race_T12_model_consumption_verified") is not False
            or meeting.get("comments_source_verified") is not False):
        raise ValueError("unfitted_prior_day_source_contract_required")
    race = meeting.get("race_code")
    if (race != manifest.get("race_code") or race != shadow.get("race_code")
            or meeting.get("racelist_original_sha256") !=
               manifest.get("official_sources", {}).get("racelist", {}).get("sha256")
            or not _SHA.fullmatch(meeting["racelist_original_sha256"])):
        raise ValueError("meeting_source_race_sha_mismatch")
    if (type(cutoff_jst) is not str or cutoff_jst != manifest.get("cutoff_jst")
            or cutoff_jst != shadow.get("t12_cutoff_jst")):
        raise ValueError("meeting_source_cutoff_mismatch")
    cutoff = datetime.fromisoformat(cutoff_jst)
    generated = datetime.fromisoformat(shadow.get("generated_at_jst", ""))
    if (cutoff.utcoffset() != timedelta(hours=9)
            or generated.utcoffset() != timedelta(hours=9)
            or generated >= cutoff):
        raise ValueError("meeting_generated_after_T12")
    refs = manifest.get("official_sources")
    if type(refs) is not dict or set(refs) != {"beforeinfo", "odds", "racelist"}:
        raise ValueError("meeting_sources_three_originals_required")
    receipts = []
    for group in refs.values():
        if (type(group) is not dict or not _SHA.fullmatch(group.get("sha256", ""))
                or type(group.get("received_at_jst")) is not str):
            raise ValueError("meeting_original_receipt_invalid")
        received = datetime.fromisoformat(group["received_at_jst"])
        if received.utcoffset() != timedelta(hours=9):
            raise ValueError("meeting_original_receipt_timezone")
        receipts.append(received)
    if max(receipts) > generated:
        raise ValueError("meeting_features_pretend_to_precede_receipt")
    six = manifest.get("six_boat_inputs")
    rows = meeting.get("rows")
    if (type(six) is not list or type(rows) is not list
            or len(six) != 6 or len(rows) != 6):
        raise ValueError("meeting_six_roster_required")
    if (sorted(v.get("exhibition_course") for v in six
               if type(v) is dict) != list(range(1, 7))
            or [v.get("lane") for v in six] != list(range(1, 7))
            or [v.get("boat") for v in rows] != list(range(1, 7))):
        raise ValueError("meeting_exhibition_course_permutation_invalid")
    url = ("https://www.boatrace.jp/owpc/pc/race/racelist"
           f"?rno={int(race[10:])}&jcd={race[8:10]}&hd={race[:8]}")
    before = ("https://www.boatrace.jp/owpc/pc/race/beforeinfo"
              f"?rno={int(race[10:])}&jcd={race[8:10]}&hd={race[:8]}")
    entry_source = {
        "source_sha256": refs["beforeinfo"]["sha256"],
        "received_at_jst": refs["beforeinfo"]["received_at_jst"],
        "source_url": before,
    }
    racers = []
    for lane, (boater, entry) in enumerate(zip(rows, six), 1):
        if (type(boater) is not dict or type(entry) is not dict
                or boater.get("registration_id") != entry.get("registration")
                or not isinstance(entry.get("registration"), str)
                or not _REG.fullmatch(entry["registration"])
                or boater.get("boat") != lane
                or entry.get("lane") != lane):
            raise ValueError("meeting_exhibition_registration_mismatch")
        history = boater.get("prior_day_results")
        n = boater.get("prior_day_completed_starts")
        top2 = boater.get("prior_day_top2_count")
        mean_st = boater.get("prior_day_average_st_s")
        if (type(history) is not list or type(n) is not int or n != len(history)
                or type(top2) is not int or not 0 <= top2 <= n
                or (n and not 0 <= mean_st < 0.5)
                or (not n and mean_st is not None)
                or any(type(v) is not dict or v.get("race_code","")[:8] >= race[:8]
                       for v in history)
                or sum(v.get("finish_position", 99) <= 2 for v in history) != top2):
            raise ValueError("meeting_historical_rate_denominator_drift")
        signals = {}
        if n:
            common = {
                "sample_size": n,
                "source_sha256": refs["racelist"]["sha256"],
                "source_url": url,
                "received_at_jst": refs["racelist"]["received_at_jst"],
            }
            signals["meeting_2ren_pct"] = dict(
                common, value=round(100 * top2 / n, 6),
                success_count=top2, denominator_kind="meeting_starts")
            signals["meeting_st_s"] = dict(
                common, value=mean_st,
                denominator_kind="meeting_start_observations")
        racers.append({
            "boat": lane,
            "exhibition_course": entry["exhibition_course"],
            "signals": signals,
            "comment": None,
        })
    claim = {
        "schema": "SCENARIO_PRE_RACE_FEATURE_CLAIMS_V1",
        "race_code": race,
        "generated_at_jst": generated.isoformat(),
        "deadline_at_jst": (cutoff + timedelta(minutes=12)).isoformat(),
        "exhibition_entry_source": entry_source,
        "racers": racers,
    }
    # Matrix construction itself is outcome-blind for target race.
    matrix = build_attack_benefit_matrix(claim)
    if matrix["count"] != 120 or matrix["predicted_probabilities"] is not False:
        raise ValueError("research_matrix_contract_broken")
    return {
        "race_code": race,
        "schema": "HISTORICAL_PRIOR_DAY_FORM_SCENARIO_FEATURE_MATRIX_ONLY_V1",
        "source_sha256": meeting["racelist_original_sha256"],
        "feature_matrix_sha256": matrix["feature_matrix_sha256"],
        "matrix": matrix,
        "replay_uses_original_saved_pre_T12_research_clock": True,
        "replay_executed_now_after_event_no_retro_candidate": True,
        "counted_meeting_form_actually_consumed_by_feature_matrix": True,
        "meeting_comment_not_consumed": True,
        "motor_rates_not_consumed_without_denominators": True,
        "deciding_method_not_inferred_from_finishes": True,
        "official_remote_first_seen_independently_verified": False,
        "new_forecast_generated": False,
        "model_coefficients_fitted": False,
        "production_changed": False,
        "formal": False,
    }
