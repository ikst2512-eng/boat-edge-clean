#!/usr/bin/env python3
"""Research-only, fail-closed audit of historical official directional-wind anchors.

Never import this file into production prediction, collector, backtest or UI.
An editorial wind statement is NOT proof of a current official venue diagram,
of a same-race original wind arrow, or of a T-12 beforeinfo receipt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "OFFICIAL_RELATIVE_WIND_EDITORIAL_ANCHOR_AUDIT_V1"
DIRECTIONS = ("北", "北東", "東", "南東", "南", "南西", "西", "北西")
ANGLE = {d: i * 45 for i, d in enumerate(DIRECTIONS)}
OFFICIAL_HOSTS = frozenset({"www.boatrace.jp", "www.boatrace-toda.jp", "www.boatrace-edogawa.com"})
VENUES = frozenset(f"{i:02d}" for i in range(1, 25))


def _relative(angle_from: int, hypothetical_heading: int) -> str:
    """Pure geometric check of candidate bearing, NOT a verified wind label."""
    d = abs((angle_from - hypothetical_heading + 180) % 360 - 180)
    if d <= 22.5:
        return "head"
    if d <= 67.5:
        return "oblique_head"
    if d <= 112.5:
        return "cross"
    if d <= 157.5:
        return "oblique_tail"
    return "tail"


def audit(rows: dict) -> dict:
    if rows.get("schema") != SCHEMA or rows.get("official_source_is_editorial_not_diagram") is not True:
        raise ValueError("wrong_provenance_or_schema")
    venues = rows.get("venues")
    if not isinstance(venues, list) or len(venues) != 24:
        raise ValueError("expected_24_venues")
    codes = [r.get("jcd") for r in venues]
    if len(set(codes)) != 24 or set(codes) != VENUES:
        raise ValueError("missing_duplicate_or_unknown_venue")
    anchored, no_anchor, A, B = [], [], 0, 0
    for r in venues:
        code = r["jcd"]
        if r.get("official_diagram_original_sha256") is not None or r.get("same_race_official_wind_arrow_sha256") is not None:
            raise ValueError("false_completed_primary_receipt:" + code)
        if r.get("official_diagram_north_checked") is not False or r.get("same_race_wind_arrow_checked") is not False:
            raise ValueError("false_primary_visual_verification:" + code)
        if r.get("t12_weather_source_sha256") is not None or r.get("production_approved") is not False:
            raise ValueError("misleading_predeadline_or_production_status:" + code)
        a = r.get("secondary_A_hypothetical_heading_deg")
        b = r.get("secondary_B_stand_facing_as_tail_deg")
        if not isinstance(a, int) or isinstance(a, bool) or a not in ANGLE.values():
            raise ValueError("invalid_secondary_A_bearing:" + code)
        if not isinstance(b, int) or isinstance(b, bool) or not 0 <= b < 360:
            raise ValueError("invalid_secondary_B_bearing:" + code)
        anchor = r.get("official_editorial_anchor")
        if anchor is None:
            if r.get("official_editorial_source_url") is not None:
                raise ValueError("source_without_specific_anchor:" + code)
            no_anchor.append(code)
            continue
        if not isinstance(anchor, dict) or set(anchor) != {"wind_from", "relative_role", "source_year", "source_note"}:
            raise ValueError("missing_precise_official_editorial_anchor:" + code)
        if anchor["wind_from"] not in DIRECTIONS or anchor["relative_role"] not in {"head", "tail"}:
            raise ValueError("ambiguous_directional_text:" + code)
        if anchor["source_year"] is not None and (not isinstance(anchor["source_year"], int) or isinstance(anchor["source_year"], bool) or not 2000 <= anchor["source_year"] <= 2026):
            raise ValueError("unknown_editorial_source_period:" + code)
        if not isinstance(anchor["source_note"], str) or len(anchor["source_note"]) < 12:
            raise ValueError("editorial_source_explanation_required:" + code)
        u = r.get("official_editorial_source_url")
        if not isinstance(u, str) or urlsplit(u).scheme != "https" or urlsplit(u).hostname not in OFFICIAL_HOSTS:
            raise ValueError("source_is_not_explicit_official_host:" + code)
        raw_direction = ANGLE[anchor["wind_from"]]
        a_label = _relative(raw_direction, a)
        b_label = _relative(raw_direction, (b + 180) % 360)
        A += a_label == anchor["relative_role"]
        B += b_label == anchor["relative_role"]
        anchored.append({"venue_code": code, "official_editorial_wind_from": anchor["wind_from"],
                         "official_editorial_role": anchor["relative_role"],
                         "secondary_A_matches": a_label == anchor["relative_role"],
                         "secondary_B_matches": b_label == anchor["relative_role"],
                         "source": u, "full_primary_visual_gate_passed": False})
    if not anchored:
        raise ValueError("no_official_editorial_evidence")
    return {
        "schema": "OFFICIAL_RELATIVE_WIND_EDITORIAL_ANCHOR_AUDIT_RESULT_V1",
        "venues_total": 24,
        "official_historical_editorial_specific_wind_anchors": len(anchored),
        "no_direct_text_anchor": len(no_anchor),
        "anchor_codes": [r["venue_code"] for r in anchored],
        "secondary_A_anchor_agreements": A,
        "secondary_B_anchor_agreements": B,
        "full_independent_diagram_and_same_race_arrow_certified_venues": 0,
        "T12_eligible_venues": 0,
        "production_wind_transform_authorized": False,
        "anchor_checks": anchored,
        "unanchored_codes": no_anchor,
        "limitations": [
            "Editorial articles are historical official commentary, not date-frozen raw official diagrams.",
            "Agreement with secondary A is not proof that A is officially correct for all 24 venues.",
            "Secondary B is a stand-facing coordinate system; treating it as tailwind is intentionally hypothetical.",
            "Official K outcome wind is postrace and cannot be a T-12 predictor.",
            "Original image SHA, north arrow reading, same-race icon, reception timestamp and forecast provenance remain missing.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.ledger.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
