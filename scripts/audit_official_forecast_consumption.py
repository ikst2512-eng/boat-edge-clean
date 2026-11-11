"""Read-only, fail-closed timing bridge: official three-source originals vs old forecasts.

A source collected after a frozen forecast cannot have been used to create it.
A source collected beforehand still does not prove model consumption. This
report never upgrades a research forecast to formal or creates a buy signal.
The official originals are independently reaudited from saved raw bytes.
"""
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from scripts.audit_three_official_t12_originals import audit_three_originals
from scripts.audit_joint_official_receipts import audit_pair

RACE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}\Z")


def read_json(path, max_size=120000):
    path = Path(path)
    if (path.is_symlink() or not path.is_file() or
            not 0 < path.stat().st_size <= max_size):
        raise ValueError("missing_or_invalid_saved_json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid_saved_json_object")
    return data


def jst(value):
    if not isinstance(value, str):
        raise ValueError("invalid_jst")
    ts = datetime.fromisoformat(value)
    if ts.utcoffset() != timedelta(hours=9):
        raise ValueError("invalid_jst_offset")
    return ts


def snapshot_timing(directory, race, official):
    """Inspect exact archived forecast only. Never use result, payout or new HTTP."""
    directory = Path(directory)
    kind = directory.name
    if kind not in ("prospective_predictions", "four_mode_forecasts"):
        raise ValueError("unexpected_forecast_type")
    path = directory / (race + ".json")
    if not path.exists() and not path.is_symlink():
        return {"status": "forecast_not_saved", "generated_at_jst": None}
    try:
        row = read_json(path)
        is_candidate = kind == "prospective_predictions"
        if is_candidate:
            if (row.get("race_code") != race or
                    row.get("status") != "prospective_candidate" or
                    row.get("formal") is not False or
                    row.get("validated") is not False or row.get("scoring") is not False):
                raise ValueError("invalid_candidate_record")
            generated = jst(row["generated_at"])
            deadline = jst(row["source_deadline_jst"])
            cutoff = jst(row["cutoff_jst"])
        else:
            if (row.get("race_code") != race or
                    row.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or
                    row.get("status") != "provisional" or
                    row.get("validated") is not False):
                raise ValueError("invalid_four_mode_record")
            generated = jst(row["generated_at_jst"])
            deadline = jst(row["deadline_jst"])
            cutoff = deadline - timedelta(minutes=12)
        title = jst(row["source_title_received_jst"])
        cards = jst(row["source_cards_received_jst"])
        if (deadline != jst(official["official_deadline_jst"]) or
                cutoff != jst(official["cutoff_jst"])):
            return {"status": "official_deadline_mismatch",
                    "generated_at_jst": generated.isoformat()}
        if not (title <= generated and cards <= generated < cutoff):
            return {"status": "forecast_timing_invalid",
                    "generated_at_jst": generated.isoformat()}
        latest = jst(official["latest_original_received_jst"])
        if latest > generated:
            status = "official_originals_arrived_after_forecast"
        else:
            # Even complete, pre-forecast official originals and a matching race
            # do NOT prove that this particular frozen model consumed them.
            status = "official_model_input_consumption_unverified"
        return {"status": status, "generated_at_jst": generated.isoformat(),
                "latest_official_received_jst": latest.isoformat(),
                "input_source_kind": str(row.get("input_source_kind", "not_recorded"))[:80],
                "formal_attested": False}
    except (ValueError, KeyError, TypeError, OSError, OverflowError, UnicodeError):
        return {"status": "forecast_record_unverified", "generated_at_jst": None}


def locate_sources(batch_dir, race, *, parts=("racelist_", "before_", "odds_")):
    observation_root = batch_dir / "observations"
    if observation_root.is_symlink() or not observation_root.is_dir():
        raise ValueError("official_sources_unavailable")
    ids = []
    for path in observation_root.glob("before_*"):
        suffix = path.name[7:]
        if IDENTIFIER.fullmatch(suffix):
            ids.append(suffix)
    if len(ids) != 1:
        raise ValueError("official_observation_identity_ambiguous")
    ident = ids[0]
    folders = []
    for prefix in parts:
        directory = observation_root / (prefix + ident) / race[:8] / race
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("official_source_directory_missing")
        filenames = ("racelist.html", "manifest.json") if prefix == "racelist_" else (
            ("beforeinfo.json", "manifest.json") if prefix == "before_" else
            ("original.html", "manifest.json"))
        if any((directory / name).is_symlink() for name in filenames):
            raise ValueError("symlink_official_source")
        folders.append(directory)
    return folders


def audit_batch(batch_dir, forecast_root, *, official_auditor=audit_three_originals, pair_auditor=audit_pair):
    """No certification is possible even when official raw evidence reaudits."""
    batch_dir, forecast_root = Path(batch_dir), Path(forecast_root)
    try:
        batch = read_json(batch_dir / "batch_report.json")
        observations = batch["observations"]
        if (batch.get("formal") is not False or batch.get("forecast_usable") is not False
                or not isinstance(observations, list) or len(observations) > 2):
            raise ValueError("invalid_research_capture_report")
    except (ValueError, KeyError, OSError, UnicodeError) as exc:
        return {"schema": "OFFICIAL_FORECAST_TEMPORAL_LINK_AUDIT_V1",
                "status": "batch_unverified", "reason": type(exc).__name__,
                "official_consumed_forecasts": 0, "formal_t12_certified": 0,
                "rows": []}
    results = []
    seen = set()
    for item in observations:
        race = item.get("race_code") if isinstance(item, dict) else None
        if not isinstance(race, str) or not RACE.fullmatch(race) or race in seen:
            return {"schema": "OFFICIAL_FORECAST_TEMPORAL_LINK_AUDIT_V1",
                    "status": "batch_unverified", "reason": "race_identity",
                    "official_consumed_forecasts": 0, "formal_t12_certified": 0,
                    "rows": []}
        seen.add(race)
        row = {"race_code": race, "official_original_status": "not_complete",
               "official_generated_forecast": False, "formal_t12_certified": False,
               "forecast_statuses": {}}
        if item.get("racecard_followup") == "three_originals_research_complete":
            try:
                dirs = locate_sources(batch_dir, race)
                audited = official_auditor(*dirs)
                declared = item["three_original_audit"]
                if (not isinstance(declared, dict) or
                        audited.get("race_code") != race or
                        audited.get("all_research_components_observed_by_t12") is not True or
                        audited.get("three_originals_hash_verified") is not True or
                        audited.get("missing_components") != [] or
                        audited.get("final_race_entry_verified") is not False or
                        audited.get("forecast_usable") is not False or
                        audited.get("full_t12_source_certified") is not False or
                        any(audited.get(k) != declared.get(k) for k in (
                            "race_code", "cutoff_jst", "official_deadline_jst",
                            "latest_original_received_jst", "t12_receipt_margin_seconds",
                            "component_checks", "missing_components"))):
                    raise ValueError("official_three_source_reaudit_mismatch")
                row["official_original_status"] = "three_originals_reaudited_research_only"
                row["latest_official_received_jst"] = audited["latest_original_received_jst"]
                row["forecast_statuses"] = {
                    name: snapshot_timing(forecast_root / name, race, audited)
                    for name in ("prospective_predictions", "four_mode_forecasts")
                }
            except (ValueError, KeyError, OSError, TypeError, UnicodeError) as exc:
                row["official_original_status"] = "official_original_reaudit_failed"
                row["reason"] = type(exc).__name__
        elif item.get("status") in ("pair_not_ready", "pair_complete"):
            # Full three-source evidence may be absent because the exhibition
            # has not published. Still independently audit the two actual raw
            # official receipts, so this run can establish whether they were
            # chronologically impossible inputs to the frozen forecast.
            try:
                before_dir, odds_dir = locate_sources(
                    batch_dir, race, parts=("before_", "odds_"))
                pair = pair_auditor(before_dir, odds_dir)
                declared = item["joint_audit"]
                if (not isinstance(declared, dict)
                        or pair.get("race_code") != race
                        or pair.get("originals_hash_verified") is not True
                        or pair.get("both_complete_before_t12") is not (
                            item["status"] == "pair_complete")
                        or any(pair.get(k) != declared.get(k) for k in (
                            "race_code", "cutoff_jst", "before_received_jst",
                            "odds_received_jst", "component_checks",
                            "missing_components", "both_complete_before_t12"))):
                    raise ValueError("official_pair_reaudit_mismatch")
                cutoff = jst(pair["cutoff_jst"])
                latest = max(jst(pair["before_received_jst"]),
                             jst(pair["odds_received_jst"]))
                observed = {
                    "official_deadline_jst": (cutoff + timedelta(minutes=12)).isoformat(),
                    "cutoff_jst": cutoff.isoformat(),
                    "latest_original_received_jst": latest.isoformat(),
                }
                row["official_original_status"] = (
                    "official_pair_complete_no_racelist_audit"
                    if pair["both_complete_before_t12"] else
                    "two_official_originals_reaudited_incomplete")
                row["source_scope"] = "official_beforeinfo_odds_only"
                row["latest_official_received_jst"] = latest.isoformat()
                row["official_received_before_t12"] = (
                    pair["component_checks"]["beforeinfo_received_by_t12"] is True
                    and pair["component_checks"]["odds_received_by_t12"] is True)
                row["forecast_statuses"] = {
                    name: snapshot_timing(forecast_root / name, race, observed)
                    for name in ("prospective_predictions", "four_mode_forecasts")
                }
            except (ValueError, KeyError, OSError, TypeError, UnicodeError) as exc:
                row["official_original_status"] = "official_pair_reaudit_failed"
                row["reason"] = type(exc).__name__
        results.append(row)
    counts = Counter(row["official_original_status"] for row in results)
    return {"schema": "OFFICIAL_FORECAST_TEMPORAL_LINK_AUDIT_V1",
            "status": "read_only_research_audited", "checked": len(results),
            "research_three_originals_reaudited": counts["three_originals_reaudited_research_only"],
            "official_pairs_reaudited": (
                counts["official_pair_complete_no_racelist_audit"] +
                counts["two_official_originals_reaudited_incomplete"]),
            "official_consumed_forecasts": 0, "formal_t12_certified": 0,
            "production_forecast": False, "purchase_approved": False,
            "rows": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", type=Path, default=Path("official_joint_evidence"))
    parser.add_argument("--forecast-root", type=Path, default=Path("."))
    args = parser.parse_args()
    report = audit_batch(args.batch_dir, args.forecast_root)
    destination = args.batch_dir / "forecast_temporal_link_report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("OFFICIAL_FORECAST_TEMPORAL_LINK " + json.dumps(report, ensure_ascii=False, sort_keys=True))
