"""F-aware original-source INPUT ONLY. Read-only, no forecast/score/archive write.

Audits the same 3 official originals, 6 registration identities, exhibition
ST flags/entry, 6 exhibition seconds, 6 nationwide win rates and 120 odds.
This never claims authenticated HTTP first-seen, final race entry, or a T-12
candidate generated when the actual old race was still underway.
"""
import hashlib
import json
import math

from scripts.audit_three_official_t12_originals import audit_three_originals
from scenario_future_archived_receipts_to_candidate import _load_receipt
from scenario_flagged_st_feature_study import encode_signed_st_only
from scenario_official_racelist_rates import extract_six_official_racelist_rates
from scenario_official_st_intake_diagnostic import _no_duplicate_keys

SCHEMA="SIGNED_F_OFFICIAL_TRIPLE_SIX_LANE_INPUT_RESEARCH_V1"


def extract_archived_signed_F_input(card_dir,beforeinfo_dir,odds_dir):
    audit=audit_three_originals(card_dir,beforeinfo_dir,odds_dir)
    if (audit["all_research_components_observed_by_t12"] is not True
            or audit["three_originals_hash_verified"] is not True
            or audit["missing_components"]!=[]
            or len(audit["component_checks"])!=12
            or not all(v is True for v in audit["component_checks"].values())):
        raise ValueError("signed_F_official_triple_not_complete")
    card,cardmeta=_load_receipt(card_dir,"racelist.html")
    before,beforemeta=_load_receipt(beforeinfo_dir,"beforeinfo.json")
    odds,oddsmeta=_load_receipt(odds_dir,"odds3t.html")
    signed=encode_signed_st_only(audit,before,beforemeta)
    rates=extract_six_official_racelist_rates(card)
    try:
        root=json.loads(before.decode("utf-8"),object_pairs_hook=_no_duplicate_keys,
                        parse_constant=lambda x: (_ for _ in ()).throw(
                            ValueError("nonfinite_official_exhibition")))
        rows=root["maindata"]["teiinfolist"]
    except (UnicodeError,ValueError,TypeError,KeyError) as exc:
        raise ValueError("official_exhibition_six_rows_invalid") from exc
    if type(rows) is not list or len(rows)!=6:
        raise ValueError("official_exhibition_six_rows_missing")
    by_boat={}
    for row in rows:
        if type(row) is not dict:
            raise ValueError("official_exhibition_racer_row_invalid")
        boat=str(row.get("teino"))
        registration=str(row.get("racerno"))
        if (boat not in {"1","2","3","4","5","6"}
                or boat in by_boat or not registration.isdigit()
                or len(registration)!=4):
            raise ValueError("official_exhibition_racer_identity_invalid")
        try:
            extime=float(row["extime"])
        except (TypeError,ValueError,KeyError,OverflowError) as exc:
            raise ValueError("official_exhibition_time_unreadable") from exc
        if not math.isfinite(extime) or not 5<=extime<=10:
            raise ValueError("official_exhibition_time_out_of_bounds")
        by_boat[boat]=(registration,extime)
    if set(by_boat)!={"1","2","3","4","5","6"}:
        raise ValueError("official_exhibition_six_unique_boats_required")
    parsed_ids={str(row["boat"]):row["registration_id"]
                for row in rates["boats"]}
    if (parsed_ids!=audit["registrations_by_lane"]
            or any(by_boat[str(i)][0]!=parsed_ids[str(i)] for i in range(1,7))):
        raise ValueError("official_racelist_beforeinfo_registration_mismatch")
    for kind,meta in (("racelist",cardmeta),("beforeinfo",beforemeta),("odds120",oddsmeta)):
        expected={"racelist":audit["racelist_received_jst"],
                  "beforeinfo":audit["beforeinfo_received_jst"],
                  "odds120":audit["odds_received_jst"]}[kind]
        if (meta.get("race_code")!=audit["race_code"]
                or meta.get("received_at_jst")!=expected):
            raise ValueError("official_triple_manifest_race_or_timestamp_mismatch")
    return {
        "schema":SCHEMA,"race_code":audit["race_code"],
        "source_sha256":{
            "racelist":hashlib.sha256(card).hexdigest(),
            "beforeinfo":hashlib.sha256(before).hexdigest(),
            "odds120":hashlib.sha256(odds).hexdigest(),
        },
        "signed_F_feature":signed,
        "six_official_racelist_national_win_rates":[
            row["national_win_rate"] for row in rates["boats"]],
        "six_official_racelist_average_st_not_used":[
            row["average_st_s"] for row in rates["boats"]],
        "six_official_exhibition_times_s":[by_boat[str(i)][1] for i in range(1,7)],
        "six_official_registration_ids":[parsed_ids[str(i)] for i in range(1,7)],
        "independent_original_component_checks":12,
        "source_originals_observed_before_T12_by_archive_audit":True,
        "official_HTTP_first_receipt_independently_verified":False,
        "candidate_first_remote_receipt_verified":False,
        "actual_final_entry_verified":False,
        "outcomes_read":False,"model_executed":False,"candidate_created":False,
        "eligible_for_existing_600":False,
        "eligible_for_future_600":False,
        "formal":False,"production_changed":False,
        "warning":"Read-only archived source replay; no forecast, official first-remote attestation or prospective sample.",
    }
