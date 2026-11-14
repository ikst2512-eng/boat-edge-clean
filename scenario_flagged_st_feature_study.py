"""Research-only, result-blind F/L exhibition ST encoding proposal.

It DOES NOT change the frozen #1693/#1710 research models or their cohort.
This is a separate, uncalibrated INPUT FEATURE STUDY. No ticket/rank output,
Git writes, realtime fetch, final entry, or formal eligibility.
"""
import hashlib
import json
from decimal import Decimal
from pathlib import Path

from scenario_official_st_intake_diagnostic import (
    BOATS, FLAGGED_ST, NUMERIC_ST, _load_receipt, _no_duplicate_keys,
    diagnose_archived_triple, diagnose_verified_source,
)

SCHEMA = "FLAGGED_EXHIBITION_ST_SIGNED_FEATURE_ONLY_V1"


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def encode_signed_st_only(audit, raw_beforeinfo, manifest):
    """Explicit F-before-zero display; L retained UNINTERPRETED.

    Return no values suitable for use by the frozen 1693 model. Later work
    needs a new future-preregistered forecast method and independent proof.
    """
    intake = diagnose_verified_source(audit, raw_beforeinfo, manifest)
    if intake["source_complete_12_of_12"] is not True:
        raise ValueError("flagged_feature_requires_all_three_complete_originals")
    # The existing read-only diagnostic has already established manifest
    # equality, race, cutoff, all six distinct exhibition course positions
    # and the accepted lexical grammar.
    try:
        data = json.loads(raw_beforeinfo.decode("utf-8"),
                          object_pairs_hook=_no_duplicate_keys,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValueError("invalid_official_nonfinite_json")))
        rows = data["maindata"]["sttenjiinfolist"]
    except (UnicodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("flagged_st_raw_unreadable") from exc
    by_boat = {}
    for row in rows:
        boat = str(row["teino"])
        course = int(row["cs"])
        st_raw = row["st"].strip()
        # L labels do NOT imply a known +1.xx seconds offset from this
        # archival string alone. Preserve exact label, no number/imputation.
        if FLAGGED_ST.fullmatch(st_raw):
            flag = st_raw[0]
            signed = ("-" + str(Decimal(st_raw[1:]))) if flag == "F" else None
        elif NUMERIC_ST.fullmatch(st_raw):
            flag = "normal"
            signed = str(Decimal(st_raw))
        else:
            raise ValueError("flagged_st_unexpected_ambiguous_string")
        by_boat[boat] = {
            "boat": int(boat),
            "exhibition_course_only": course,
            "official_st_raw": st_raw,
            "display_class": flag,
            "signed_st_seconds_decimal_string": signed,
            "numeric_model_input_authorized": False,
        }
    if set(by_boat) != BOATS:
        raise ValueError("signed_st_six_boats_required")
    ordered = [by_boat[str(i)] for i in range(1, 7)]
    count_F = sum(v["display_class"] == "F" for v in ordered)
    count_L = sum(v["display_class"] == "L" for v in ordered)
    vector = {
        "race_code": intake["race_code"],
        "beforeinfo_source_sha256": hashlib.sha256(raw_beforeinfo).hexdigest(),
        "exhibition_st_by_boat": ordered,
    }
    return {
        "schema": SCHEMA,
        "study_scope": "separate_exploratory_feature_encoding_no_forecast",
        "frozen_1693_1710_method_changed": False,
        "source_complete_12_of_12": True,
        "race_code": intake["race_code"],
        "beforeinfo_source_sha256": vector["beforeinfo_source_sha256"],
        "vector_sha256": hashlib.sha256(_canonical(vector)).hexdigest(),
        "exhibition_st_by_boat": ordered,
        "flag_F_count": count_F,
        "flag_L_count": count_L,
        "numeric_display_count": 6 - count_F - count_L,
        "signed_numeric_available_for_all_six": count_L == 0,
        "flagged_display_is_main_race_F_or_L": False,
        "F_label_interpreted_as_before_zero_only": True,
        "L_display_time_offset_independently_verified": False,
        "signed_feature_calibrated": False,
        "model_executed": False,
        "candidate_created": False,
        "official_first_remote_receipt_verified": False,
        "candidate_first_remote_receipt_verified": False,
        "eligible_for_existing_300_plus_300": False,
        "formal": False,
        "accuracy_improvement_proven": False,
        "production_changed": False,
        "warning": (
            "An exploratory sign-preserving feature display, NOT a model "
            "prediction or an amendment to any preregistered frozen method."
        ),
    }


def encode_archived_triple(card_dir, beforeinfo_dir, odds_dir):
    # Audit all official originals first; an old saved race is never
    # promoted to a prospective candidate by this read-only inspection.
    from scripts.audit_three_official_t12_originals import audit_three_originals
    audit = audit_three_originals(card_dir, beforeinfo_dir, odds_dir)
    raw, manifest = _load_receipt(beforeinfo_dir, "beforeinfo.json")
    return encode_signed_st_only(audit, raw, manifest)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Read-only F/L signed research feature, never forecasts")
    for name in ("card-dir", "before-dir", "odds-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    print(json.dumps(encode_archived_triple(args.card_dir, args.before_dir, args.odds_dir),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
