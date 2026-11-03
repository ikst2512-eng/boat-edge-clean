"""Fail-closed race-ID reconciliation between real capture artifacts and durable ledger.

Read ONLY existing independent stage reports; never recompute or reconstruct
candidate tickets from outcomes. Capture report is a bounded window, not a
complete lifetime inventory; the ledger may contain older entries.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

TOPS = ("top3", "top5", "top10")
FIELDS = ("baseline", "candidate", "gained", "lost")


def paired_scores(report):
    """Read exact same-race TopN scores; reject missing or malformed evidence."""
    paired = report.get("paired")
    scores = report.get("paired_race_scores")
    codes = report.get("race_codes_paired")
    if (type(paired) is not int or paired < 0
            or type(scores) is not list or type(codes) is not list
            or len(scores) != paired or len(codes) != paired
            or len(set(codes)) != len(codes)):
        raise ValueError("invalid_paired_score_roster")
    mapping = {}
    for row in scores:
        if type(row) is not dict or type(row.get("race_code")) is not str:
            raise ValueError("invalid_paired_score_row")
        code = row["race_code"]
        if code not in codes or code in mapping:
            raise ValueError("invalid_paired_score_identity")
        topn = row.get("topn")
        if type(topn) is not dict or set(topn) != set(TOPS):
            raise ValueError("invalid_paired_score_topn")
        verified = {}
        for n in TOPS:
            values = topn[n]
            if (type(values) is not dict or set(values) != set(FIELDS)
                    or any(type(values[k]) is not int
                           or values[k] not in (0, 1) for k in FIELDS)
                    or values["candidate"] - values["baseline"]
                       != values["gained"] - values["lost"]
                    or values["gained"] and values["lost"]):
                raise ValueError("invalid_paired_score_value")
            verified[n] = dict(values)
        mapping[code] = verified
    if set(mapping) != set(codes):
        raise ValueError("paired_score_roster_disagrees")
    return mapping

def reconcile(capture, ledger, *, before_future_start=False):
    if (type(capture) is not dict or type(ledger) is not dict
            or capture.get("schema") != "V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1"
            or ledger.get("schema") != "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1"):
        raise ValueError("invalid_audit_schema")
    out = {
        "schema": "V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1",
        "formal": False, "remote_first_seen_independently_verified": False,
        "production_promotion_allowed": False,
        "status": "unverified",
        "capture_frozen": capture.get("frozen"),
        "ledger_frozen": ledger.get("frozen"),
        "capture_codes": [], "missing_from_ledger": [],
        "additional_ledger_codes": [],
        "capture_paired": capture.get("paired"),
        "ledger_paired": ledger.get("paired"),
        "paired_score_mismatch_codes": [],
        "paired_result_coverage_mismatch_codes": [],
        "warning": "A bounded run inventory and Git history are not independent remote-first-seen proof.",
    }
    left = capture.get("race_codes_frozen")
    right = ledger.get("race_codes_frozen")
    if (type(left) is not list or type(right) is not list
            or any(type(x) is not str or len(x) != 12 or not x.isdigit()
                   for x in left + right)
            or len(set(left)) != len(left) or len(set(right)) != len(right)
            or type(capture.get("frozen")) is not int or type(ledger.get("frozen")) is not int
            or capture["frozen"] != len(left) or ledger["frozen"] != len(right)):
        raise ValueError("invalid_frozen_race_rosters")
    out["capture_codes"] = sorted(left)
    out["missing_from_ledger"] = sorted(set(left) - set(right))
    out["additional_ledger_codes"] = sorted(set(right) - set(left))
    # Identical hit flags do not prove that the underlying frozen tickets
    # were identical. Compare ordered baseline/candidate digest by race.
    def validated_hashes(report, codes):
        hashes = report.get("frozen_ticket_hashes")
        if (type(hashes) is not dict
                or not set(hashes).issubset(set(codes))
                or any(type(code) is not str
                       or type(value) is not str
                       or not re.fullmatch(r"[a-f0-9]{64}", value)
                       for code, value in hashes.items())):
            return None
        return hashes

    left_hashes = validated_hashes(capture, left)
    right_hashes = validated_hashes(ledger, right)
    out["frozen_ticket_mismatch_codes"] = []
    # Matching IDs are not sufficient when either upstream producer has an
    # unknown/contradictory result status. Only an explicitly scored bounded
    # capture and a valid durable rollup can establish a matched roster.
    capture_scored = capture.get("status") == "frozen_artifacts_scored_limited_cohort"
    ledger_scored = ledger.get("status") == "durable_frozen_evidence_scored"
    # Before the first valid future freeze the durable branch can legitimately
    # have zero research records. That is a zero denominator, not corruption.
    # Never allow this exemption if either side lists a frozen race.
    empty_ledger = (ledger.get("status") == "no_long_lived_frozen_evidence"
                    and ledger["frozen"] == 0 and not right
                    and not ledger.get("invalid_files"))
    # Before the prospective study starts (Nov 4 JST), there cannot be a
    # future frozen capture. This is a zero denominator, not a missing
    # production result. Keep every nonempty/failed/incomplete report blocked.
    prestart_empty = (
        before_future_start
        and capture.get("status") == "no_future_capture_runs"
        and capture.get("eligible_runs_in_inventory") == 0
        and capture.get("selected_runs") == 0
        and capture.get("pending_or_unknown_runs") == 0
        and capture.get("unsuccessful_runs") == 0
        and capture.get("inventory_limit_reached") is False
        and not capture.get("missing_or_failed_artifacts")
        and not capture.get("bad_validation_runs")
        and capture.get("frozen") == 0 and capture.get("paired") == 0
        and not left and empty_ledger and not right
    )
    if prestart_empty:
        out["status"] = "prestart_no_future_capture_runs"
        return out
    if (not capture_scored
            or capture.get("cohort_completeness_verified") is not True
            or capture.get("missing_or_failed_artifacts")
            or capture.get("bad_validation_runs")):
        out["status"] = "incomplete_capture_inventory"
    elif (not (ledger_scored or (not left and empty_ledger))
          or ledger.get("invalid_files")):
        out["status"] = "invalid_or_unavailable_ledger"
    elif out["missing_from_ledger"]:
        out["status"] = "frozen_predictions_missing_from_ledger"
    elif (left_hashes is None or right_hashes is None
          or set(left_hashes) != set(left)
          or not set(left).issubset(set(right_hashes))):
        out["status"] = "frozen_ticket_digest_evidence_missing_or_invalid"
    elif left and any(left_hashes[code] != right_hashes[code] for code in left):
        out["frozen_ticket_mismatch_codes"] = sorted(
            code for code in left if left_hashes[code] != right_hashes[code])
        out["status"] = "frozen_ticket_digest_mismatch"
    elif left:
        try:
            capture_scores = paired_scores(capture)
            ledger_scores = paired_scores(ledger)
        except ValueError:
            out["status"] = "paired_score_evidence_missing_or_invalid"
        else:
            # Both sides must agree on which races in this bounded
            # capture cohort already have confirmed results. Ignore older
            # ledger-only frozen races outside the capture roster.
            capture_frozen_codes = set(left)
            out["paired_result_coverage_mismatch_codes"] = sorted(
                set(capture_scores).symmetric_difference(
                    set(ledger_scores) & capture_frozen_codes))
            out["paired_score_mismatch_codes"] = sorted(
                code for code in set(capture_scores) & set(ledger_scores)
                if capture_scores[code] != ledger_scores[code])
            out["status"] = (
                "paired_result_coverage_mismatch"
                if out["paired_result_coverage_mismatch_codes"] else
                "paired_topn_score_mismatch"
                if out["paired_score_mismatch_codes"] else
                "bounded_frozen_roster_matched")
    else:
        out["status"] = "no_frozen_predictions_to_compare"
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # An upstream stage can fail before writing its own report. Persist a
    # diagnostic artifact identifying the unavailable input rather than
    # losing the final reconciliation JSON to an uncaught file/JSON error.
    missing = []
    invalid = []
    values = {}
    for name, path in (("capture", args.capture), ("ledger", args.ledger)):
        try:
            values[name] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            missing.append(name)
        except (OSError, UnicodeError, json.JSONDecodeError):
            invalid.append(name)
    if missing or invalid:
        report = {
            "schema": "V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1",
            "status": "reconciliation_inputs_unavailable",
            "formal": False,
            "remote_first_seen_independently_verified": False,
            "production_promotion_allowed": False,
            "missing_input_reports": missing,
            "invalid_input_reports": invalid,
            "warning": "Upstream capture or ledger stage did not supply valid report JSON.",
        }
    else:
        try:
            report = reconcile(
                values["capture"], values["ledger"],
                before_future_start=datetime.now(timezone.utc) < datetime(
                    2026, 11, 3, 15, 0, tzinfo=timezone.utc))
        except (ValueError, TypeError, KeyError):
            report = {
                "schema": "V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1",
                "status": "reconciliation_input_schema_invalid",
                "formal": False,
                "remote_first_seen_independently_verified": False,
                "production_promotion_allowed": False,
                "invalid_input_reports": ["capture", "ledger"],
                "warning": "One or both upstream reports violate the reconciliation schema.",
            }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("V2_THIRD_RATE_LEDGER_RECONCILIATION=" + json.dumps(report, sort_keys=True))
    if report["status"] in ("reconciliation_inputs_unavailable",
                            "reconciliation_input_schema_invalid",
                            "incomplete_capture_inventory",
                            "frozen_predictions_missing_from_ledger",
                            "invalid_or_unavailable_ledger",
                            "paired_score_evidence_missing_or_invalid",
                            "paired_result_coverage_mismatch",
                            "paired_topn_score_mismatch",
                            "frozen_ticket_digest_evidence_missing_or_invalid",
                            "frozen_ticket_digest_mismatch"):
        raise SystemExit(2)
