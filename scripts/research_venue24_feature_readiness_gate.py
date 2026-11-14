#!/usr/bin/env python3
"""Fail-closed, research-only #1692 -> #1708 source/provenance handoff validator.

This validates a snapshot of descriptive evidence, NOT any permission to use it
in production. No network, no forecasting code, no new data download.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

FROZEN_SCHEMA = "BOAT_EDGE_24_VENUE_FEATURE_SOURCE_AND_T12_READINESS_V1"
SOURCE_PATHS = (
    "docs/research/venue_environment_baseline_20261106.csv",
    "docs/research/official_water_24venue_png_sha256_ledger_20261109.json",
    "docs/research/official_water_24venue_compass_visual_firstpass_20261109.json",
    "docs/research/official_k_92day_c2_escape_and_attack_24venue_20261109.csv",
)
GROUPS = (
    "venue_static_water", "course_baseline", "official_water_diagram",
    "relative_wind", "wind_speed_and_wave", "tide",
    "course2_escape_proxy", "course2_sashi", "course3_4_attack",
    "wall_predictor", "exhibition_and_motor",
)

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()

def get_source(root: Path, relative: str, expected: str):
    if not relative.startswith("docs/research/") or ".." in Path(relative).parts:
        raise ValueError("source_path_outside_research")
    p = root / relative
    if p.is_symlink() or not p.is_file():
        raise ValueError("source_missing_or_symlink:" + relative)
    raw = p.read_bytes()
    if git_blob_sha(raw) != expected:
        raise ValueError("source_git_blob_sha_changed:" + relative)
    return raw

def validate(doc: dict, source_contents: dict[str, bytes]) -> dict:
    if doc.get("schema") != FROZEN_SCHEMA:
        raise ValueError("schema_unrecognized")
    if doc.get("baseline_period") != "2026-08-01/2026-10-31":
        raise ValueError("period_drift")
    if doc.get("status") != "research_handoff_fail_closed":
        raise ValueError("research_only_status_required")
    gov = doc.get("governance") or {}
    if not all(gov.get(k) is True for k in (
        "source_received_flag_is_not_feature_predeadline_eligibility",
        "postrace_k_cannot_be_used_as_same_race_prediction_input",
        "unknown_missing_values_never_zero_imputed",
    )):
        raise ValueError("leakage_and_missingness_gate")
    if gov.get("forecast_effect_proven_new_features") != 0 or gov.get("production_model_changed") is not False or gov.get("auto_merge_main") is not False:
        raise ValueError("research_to_production_promotion_forbidden")
    original = doc.get("provenance") or {}
    mapping = (
        "venue_baseline", "official_water_diagram",
        "diagram_single_Ai_view", "official_K_course2_counts",
    )
    for key, path in zip(mapping, SOURCE_PATHS):
        item = original.get(key) or {}
        if item.get("file") != path or not isinstance(item.get("git_blob_sha"), str):
            raise ValueError("missing_frozen_provenance:" + key)
        if path not in source_contents or git_blob_sha(source_contents[path]) != item["git_blob_sha"]:
            raise ValueError("unmatched_source_git_blob:" + path)
    if original.get("official_K_raw_artifact_zip_sha256") != "c668f545bae54f8148616315e307ed2a2b04a77a0cb8abf88bf3ea078749ce8e":
        raise ValueError("official_K_original_artifact_sha_unfrozen")
    base_rows = list(csv.DictReader(source_contents[SOURCE_PATHS[0]].decode("utf-8-sig").splitlines()))
    c2_rows = list(csv.DictReader(source_contents[SOURCE_PATHS[3]].decode("utf-8-sig").splitlines()))
    water_rows = json.loads(source_contents[SOURCE_PATHS[1]])["venues"]
    visual_rows = json.loads(source_contents[SOURCE_PATHS[2]])["venues"]
    if not all(len(a) == 24 for a in (base_rows, c2_rows, water_rows, visual_rows)):
        raise ValueError("source_venue_count_not_24")
    base = {r["venue_code"]: r for r in base_rows}
    c2 = {r["jcd"]: r for r in c2_rows}
    water = {r["jcd"]: r for r in water_rows}
    visual = {r["jcd"]: r for r in visual_rows}
    rows = doc.get("venues")
    if not isinstance(rows, list) or len(rows) != 24:
        raise ValueError("venue_count_not_24")
    expected = {f"{i:02d}" for i in range(1, 25)}
    codes = [r.get("venue_code") for r in rows]
    if len(set(codes)) != 24 or set(codes) != expected:
        raise ValueError("venue_codes_missing_or_duplicate")
    eligible = 0
    priorities = []
    for r in rows:
        code = r["venue_code"]
        g = r.get("feature_status")
        if not isinstance(g, dict) or set(g) != set(GROUPS):
            raise ValueError("feature_groups_missing_or_changed:" + code)
        if r.get("venue_name") != base[code]["venue_name"] or r.get("official_stadium_url") != base[code]["official_source_url"]:
            raise ValueError("venue_static_source_mismatch:" + code)
        if r.get("production_authorized_feature_keys") != [] or r.get("head_to_head_model_effect_proven") is not False or r.get("missingness_treated_as") != "unknown_not_zero":
            raise ValueError("production_or_unknown_fail_closed:" + code)
        original_png = g["official_water_diagram"]
        if original_png.get("sha256") != water[code]["sha256"] or original_png.get("official_source_url") != water[code]["official_url"] or original_png.get("independent_two_reviewers_confirmed") is not False or original_png.get("official_arrow_from_to_verified") is not False or original_png.get("schematic_bearing_approved") is not False:
            raise ValueError("original_png_or_arrow_gate:" + code)
        if g["course_baseline"].get("course_win_percent") != [float(base[code][f"c{i}_win_pct"]) for i in range(1,7)]:
            raise ValueError("course_rate_drift:" + code)
        if g["tide"].get("tidal_effect_memo") != base[code]["tidal_change"] or g["tide"].get("tide_flow_vector") is not None or g["tide"].get("measured_tide_height_at_race") is not None:
            raise ValueError("unobserved_tide_must_remain_unknown:" + code)
        if g["relative_wind"].get("model_relative_head_tail") is not None or g["relative_wind"].get("relative_direction_certified") is not False:
            raise ValueError("unapproved_relative_wind:" + code)
        if g["relative_wind"].get("research_priority_secondary_disagreement") is not bool(visual[code]["requires_priority_second_read"]):
            raise ValueError("compass_prior_mismatch:" + code)
        if g["relative_wind"]["research_priority_secondary_disagreement"]:
            priorities.append(code)
        for key in GROUPS:
            if g[key].get("forecast_effect_proven") is not False:
                raise ValueError("effect_unproved_must_be_false:" + code + ":" + key)
            if key not in ("venue_static_water", "course_baseline", "official_water_diagram") and g[key].get("predeadline_eligible") is not False:
                raise ValueError("predeadline_evidence_missing:" + code + ":" + key)
        c2proxy = g["course2_escape_proxy"]
        if c2proxy.get("is_athlete_specific_c2_escapement_rate") is not False or c2proxy.get("cohort_eligible") != int(c2[code]["eligible"]) or c2proxy.get("c1_escape_with_valid_2C_count") != int(c2[code]["c1_escape_count"]):
            raise ValueError("c2_proxy_vs_true_wall_mismatch:" + code)
        eligible += c2proxy["cohort_eligible"]
        if g["course2_sashi"].get("count") != int(c2[code]["c2_sashi_count"]):
            raise ValueError("c2_method_cohort_mismatch:" + code)
        if g["course3_4_attack"].get("course3_makuri_count") != int(c2[code]["c3_makuri_count"]) or g["course3_4_attack"].get("course4_makuri_count") != int(c2[code]["c4_makuri_count"]):
            raise ValueError("c3c4_attack_cohort_mismatch:" + code)
    expected_counts = doc.get("counts") or {}
    if eligible != 13815 or eligible != expected_counts.get("official_K_C2_analysis_eligible_races"):
        raise ValueError("eligible_denominator_drift")
    if expected_counts.get("venues") != 24 or expected_counts.get("new_model_effect_proven_features") != 0:
        raise ValueError("counts_promoted")
    if expected_counts.get("official_water_diagram_raw_png_receipts") != 24 or expected_counts.get("diagram_independent_two_reviewer_certified") != 0 or expected_counts.get("official_same_race_arrow_verified_venues") != 0:
        raise ValueError("diagram_or_arrow_counts_promoted")
    if expected_counts.get("predeadline_tide_height_verified_venues") != 0 or expected_counts.get("predeadline_wind_evidence_in_saved_368_forecasts") != 0:
        raise ValueError("tide_wind_missingness_counts_promoted")
    if priorities != expected_counts.get("priority_AI_compass_disagreement_venues"):
        raise ValueError("priority_counts_changed")
    return {"venues": 24, "source_git_blob_sha_checked": 4, "cohort_eligible": eligible,
            "priority_visual_review": priorities, "approved_model_features": 0,
            "official_same_race_wind_arrow_verified": 0}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--ledger", default="docs/research/venue24_feature_readiness_handoff_20261109.json")
    args = p.parse_args()
    path = args.repo_root / args.ledger
    if path.is_symlink() or not path.is_file():
        raise ValueError("ledger_missing_or_symlink")
    doc = json.loads(path.read_text(encoding="utf-8"))
    originals = {}
    for key in ("venue_baseline","official_water_diagram","diagram_single_Ai_view","official_K_course2_counts"):
        entry = doc["provenance"][key]
        originals[entry["file"]] = get_source(args.repo_root, entry["file"], entry["git_blob_sha"])
    print(json.dumps(validate(doc, originals), ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
