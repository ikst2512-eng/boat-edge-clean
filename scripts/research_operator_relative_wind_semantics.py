#!/usr/bin/env python3
"""Research-only official operator WIND LABEL semantic gate; not a forecast feature.

The official operator's dynamically rendered motor history can reveal textual
8-direction -> broad wind labels, but is neither a byte-frozen source receipt
nor proof of 2026 stadium geometry, weather arrow FROM/TO, or T-12 eligibility.
Never import into production or alter existing prediction, UI, CI, or cron.
"""
from __future__ import annotations

import argparse
import json
from urllib.parse import urlsplit
from pathlib import Path

SCHEMA = "BOAT_EDGE_OPERATOR_RELATIVE_WIND_8_DIRECTION_TEXT_AUDIT_V1"
DEGREES = {"北": 0, "北東": 45, "東": 90, "南東": 135,
           "南": 180, "南西": 225, "西": 270, "北西": 315}
VALID_LABELS = {"向い風", "追い風", "左横風", "右横風"}
OFFICIAL_HOSTS = frozenset({"boatrace-ashiya.com", "www.boatrace-ashiya.com"})
CANDIDATES = range(0, 360, 45)
FROZEN_FLAGS = (
    "source_document_sha256", "water_diagram_original_png_sha256",
    "original_same_race_wind_arrow_sha256", "t12_beforeinfo_original_sha256"
)
REQUIRED_FALSE = (
    "official_diagram_second_reader_signed_off",
    "raw_html_frozen_and_replayable",
    "operator_label_semantics_approved_for_all_venues",
    "formal_heading_certified", "t12_eligible",
    "production_authorized", "main_modified"
)

def relative_5(wind_from_degrees: int, candidate_heading_degrees: int) -> str:
    """Only a geometric candidate; does not certify an actual stadium axis."""
    delta = (wind_from_degrees - candidate_heading_degrees + 180) % 360 - 180
    d = abs(delta)
    if d <= 22.5:
        return "head"
    if d <= 67.5:
        return "oblique_head"
    if d <= 112.5:
        return "cross_left" if delta < 0 else "cross_right"
    if d <= 157.5:
        return "oblique_tail"
    return "tail"

def operator_coarse(candidate_sector: str) -> str:
    return {
        "head": "向い風", "oblique_head": "向い風",
        "cross_left": "左横風", "cross_right": "右横風",
        "oblique_tail": "追い風", "tail": "追い風"
    }[candidate_sector]

def official_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS
            and parsed.username is None and parsed.password is None
            and parsed.path.startswith("/sp/"))

def audit(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("site_code") != "21":
        raise ValueError("unsupported_operator_source_or_schema")
    if data.get("evidence_type") != "operator_public_rendered_text_without_origin_raw_html_sha":
        raise ValueError("unsupported_receipt_class")
    if any(data.get(k) is not None for k in FROZEN_FLAGS):
        raise ValueError("unsupported_raw_sha_claim")
    if any(data.get(k) is not False for k in REQUIRED_FALSE):
        raise ValueError("premature_certification_or_production_use")
    rows = data.get("source_rows")
    if not isinstance(rows, list) or len(rows) != 8:
        raise ValueError("eight_direction_evidence_required")
    winds = [row.get("wind_from") if isinstance(row, dict) else None for row in rows]
    if set(winds) != set(DEGREES) or len(set(winds)) != 8:
        raise ValueError("wind_direction_incomplete_or_duplicate")
    for row in rows:
        if (row.get("operator_label") not in VALID_LABELS
                or row.get("original_html_sha256") is not None
                or row.get("observed_source_type") != "operator_motor_history_public_text_rendering_not_raw_receipt"
                or not official_url(row.get("source_url"))):
            raise ValueError("operator_text_or_source_unverified:" + str(row.get("wind_from")))
    calm = data.get("calm_row")
    if not isinstance(calm, dict) or not (
        calm.get("wind_from") == calm.get("operator_label") == "無風"
        and calm.get("wind_m") == 0 and calm.get("original_html_sha256") is None
        and official_url(calm.get("source_url"))
    ):
        raise ValueError("calm_direction_must_remain_separate")
    per_axis = []
    for heading in CANDIDATES:
        observations = [{
            "wind_from": row["wind_from"], "operator_label": row["operator_label"],
            "candidate_sector": relative_5(DEGREES[row["wind_from"]], heading),
            "candidate_operator_group": operator_coarse(relative_5(DEGREES[row["wind_from"]], heading)),
        } for row in rows]
        matched = sum(x["operator_label"] == x["candidate_operator_group"] for x in observations)
        per_axis.append({"hypothetical_heading_deg": heading, "agree": matched,
                         "all_eight_agree": matched == 8})
    exact_fit = [r["hypothetical_heading_deg"] for r in per_axis if r["all_eight_agree"]]
    if not exact_fit:
        raise ValueError("operator_examples_have_no_consistent_8point_axis")
    return {
        "schema": "BOAT_EDGE_OPERATOR_WIND_TEXT_GEOMETRY_HYPOTHESIS_ONLY_V1",
        "venue_code": "21", "source_rows": 8, "calm_is_unmapped": True,
        "angle_candidates": per_axis, "consistent_candidate_angles_deg": exact_fit,
        "hypothesis_only_not_official_heading": True,
        "original_html_bytes_verified": False, "original_diagram_png_verified": False,
        "same_race_wind_arrow_verified": False, "T12_weather_eligible": False,
        "production_wind_transform_authorized": False
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(audit(json.loads(a.source.read_text(encoding="utf-8"))),
                     ensure_ascii=False, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
