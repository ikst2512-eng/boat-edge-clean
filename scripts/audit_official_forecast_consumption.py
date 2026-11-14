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


def snapshot_timing(directory, race, official, *, independent_beforeinfo_sha256=None):
    """Inspect exact archived forecast only. Never use result, payout or new HTTP."""
    directory = Path(directory)
    kind = directory.name
    if kind not in ("prospective_predictions", "four_mode_forecasts",
                    "scenario_forecasts", "v133_policy_forecasts"):
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
        elif kind == "four_mode_forecasts":
            if (row.get("race_code") != race or
                    row.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or
                    row.get("status") != "provisional" or
                    row.get("validated") is not False):
                raise ValueError("invalid_four_mode_record")
            generated = jst(row["generated_at_jst"])
            deadline = jst(row["deadline_jst"])
            cutoff = deadline - timedelta(minutes=12)
        else:
            # New scenario/V133 records are separate, uncalibrated research
            # artifacts. They consume a verified racecard/beforeinfo receipt,
            # NOT necessarily this separately collected official three-original
            # batch. The chronology can reject impossible provenance but can
            # never affirm positive consumption without exact input linkage.
            identity = {
                "scenario_forecasts": (
                    "CLEAN_RESTORED_SCENARIO_FORWARD_CAPTURE_V1",
                    "predeadline_frozen_scenario_research"),
                "v133_policy_forecasts": (
                    "CLEAN_V133_POINT_POLICY_PROSPECTIVE_RESEARCH_V1",
                    "predeadline_v133_policy_research_frozen"),
            }[kind]
            if (row.get("race_code") != race or
                    row.get("schema") != identity[0] or
                    row.get("status") != identity[1] or
                    row.get("formal") is not False or
                    row.get("calibrated") is not False or
                    row.get("first_remote_add_verified") is not False or
                    row.get("production_buy_approved") is not False or
                    row.get("v2_archive_untouched") is not True):
                raise ValueError("invalid_scenario_research_record")
            generated = jst(row["generated_at_jst"])
            deadline = jst(row["deadline_jst"])
            cutoff = deadline - timedelta(minutes=12)
            audit = row.get("source_audit")
            if not isinstance(audit, dict):
                raise ValueError("scenario_source_audit_missing")
            for name in ("race_card", "beforeinfo"):
                receipt = audit.get(name)
                if not isinstance(receipt, dict) or receipt.get("status") != "ok":
                    raise ValueError("scenario_source_receipt_unverified")
            if (audit["race_card"].get("sha256") !=
                    row.get("source_racecard_sha256")):
                raise ValueError("scenario_racecard_digest_mismatch")
            # The model-reported beforeinfo digest is not independently
            # attested, but we can explicitly compare it with a separately
            # hash-rechecked official original from the SAME race. A match
            # alone cannot establish that the model actually consumed it.
            model_beforeinfo_sha = audit["beforeinfo"].get("sha256")
            if (not isinstance(model_beforeinfo_sha, str)
                    or re.fullmatch(r"[a-f0-9]{64}", model_beforeinfo_sha) is None):
                raise ValueError("scenario_beforeinfo_digest_invalid")
            title = jst(audit["race_card"]["fetched_at"])
            cards = jst(audit["beforeinfo"]["fetched_at"])
        if is_candidate or kind == "four_mode_forecasts":
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
        input_digest_check = {
            "status": "not_applicable_to_this_forecast_type",
            "model_reported_beforeinfo_sha256": None,
            "independent_original_beforeinfo_sha256": None,
            "identical_original_proven_used": False,
        }
        if kind in ("scenario_forecasts", "v133_policy_forecasts"):
            input_digest_check["model_reported_beforeinfo_sha256"] = model_beforeinfo_sha
            if independent_beforeinfo_sha256 is None:
                input_digest_check["status"] = "independent_original_digest_unavailable"
            else:
                if (not isinstance(independent_beforeinfo_sha256, str)
                        or re.fullmatch(r"[a-f0-9]{64}", independent_beforeinfo_sha256) is None):
                    raise ValueError("independent_beforeinfo_digest_invalid")
                input_digest_check["independent_original_beforeinfo_sha256"] = (
                    independent_beforeinfo_sha256)
                input_digest_check["status"] = (
                    "reported_hash_equal_consumption_unverified"
                    if model_beforeinfo_sha == independent_beforeinfo_sha256
                    else "reported_hash_differs_from_independent_original"
                )
        return {"status": status, "generated_at_jst": generated.isoformat(),
                "latest_official_received_jst": latest.isoformat(),
                "input_source_kind": str(row.get("input_source_kind",
                    row.get("source_audit", {}).get("beforeinfo", {}).get("source",
                            "not_recorded")))[:80],
                "independent_beforeinfo_digest_comparison": input_digest_check,
                "formal_attested": False}
    except (ValueError, KeyError, TypeError, OSError, OverflowError, UnicodeError):
        return {"status": "forecast_record_unverified", "generated_at_jst": None}



def verified_official_input_manifest(dirs, audited):
    """Read-only six-lane input reconstruction from verified official bytes.

    This does NOT prove that any predictor consumed the fields. No new forecast
    is generated and no retrospective first Git receipt is attested.
    """
    import hashlib
    import math
    cutoff = jst(audited["cutoff_jst"])
    if (audited.get("all_research_components_observed_by_t12") is not True
            or audited.get("three_originals_hash_verified") is not True
            or audited.get("missing_components") != []
            or audited.get("final_race_entry_verified") is not False
            or jst(audited["latest_original_received_jst"]) >= cutoff):
        raise ValueError("official_input_not_prospectively_complete")
    race = audited["race_code"]
    source_map = {}
    raw_before = None
    for kind, directory, filename in zip(
            ("racelist", "beforeinfo", "odds"), dirs,
            ("racelist.html", "beforeinfo.json", "original.html")):
        path = Path(directory) / filename
        meta = read_json(Path(directory) / "manifest.json")
        if path.is_symlink() or not path.is_file():
            raise ValueError("official_input_source_invalid")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        received = jst(meta["received_at_jst"])
        if (meta.get("race_code") != race or meta.get("sha256") != digest
                or meta.get("bytes") != len(raw) or not raw or received > cutoff):
            raise ValueError("official_input_raw_or_clock_mismatch")
        source_map[kind] = {"sha256": digest, "bytes": len(raw),
                            "received_at_jst": received.isoformat()}
        if kind == "beforeinfo":
            raw_before = raw
    before = json.loads(raw_before)["maindata"]
    if (not isinstance(before, dict) or str(before.get("hd")) != race[:8]
            or str(before.get("jcd")).zfill(2) != race[8:10]
            or str(before.get("rno")) != str(int(race[10:]))):
        raise ValueError("official_input_race_identity_invalid")

    def six_by_lane(rows):
        if not isinstance(rows, list) or len(rows) != 6:
            raise ValueError("official_input_six_rows_missing")
        found = {}
        for r in rows:
            if not isinstance(r, dict) or str(r.get("teino")) not in ("1","2","3","4","5","6"):
                raise ValueError("official_input_lane_invalid")
            lane = str(r["teino"])
            if lane in found:
                raise ValueError("official_input_lane_duplicate")
            found[lane] = r
        return found

    boats = six_by_lane(before.get("teiinfolist"))
    starts = six_by_lane(before.get("sttenjiinfolist"))
    rows, courses = [], {}
    for lane in range(1, 7):
        key = str(lane)
        b, s = boats[key], starts[key]
        registration, st = str(b.get("racerno")), s.get("st")
        if registration != audited["registrations_by_lane"].get(key):
            raise ValueError("official_input_registration_mismatch")
        try:
            time, tilt, course = float(b["extime"]), float(b["tilt"]), int(s["cs"])
        except (KeyError, ValueError, TypeError, OverflowError):
            raise ValueError("official_input_measurement_invalid") from None
        if (not math.isfinite(time) or not 5 <= time <= 9
                or not math.isfinite(tilt) or not -1 <= tilt <= 3
                or type(st) is not str
                or not re.fullmatch(r"(?:[FL])?\.\d{1,2}|\d?\.\d{1,2}", st.strip())
                or course not in range(1, 7) or str(course) in courses):
            raise ValueError("official_input_measurement_invalid")
        courses[str(course)] = key
        rows.append({"lane": lane, "registration": registration,
                     "exhibition_time": time, "tilt": tilt,
                     "exhibition_st": st.strip(), "exhibition_course": course})
    if courses != audited["exhibition_course_to_boat"]:
        raise ValueError("official_input_course_mismatch")
    inputs = {"race_code": race, "cutoff_jst": cutoff.isoformat(),
              "official_sources": source_map, "six_boat_inputs": rows}
    input_digest = hashlib.sha256(json.dumps(
        inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {"schema": "OFFICIAL_REAUDITED_INPUT_MANIFEST_V1",
            **inputs, "input_sha256": input_digest,
            "official_source_fields_reconstructed": True,
            "model_actually_consumed_fields": False,
            "independent_remote_first_seen_verified": False,
            "final_race_entry_verified": False,
            "formal_t12_certified": False, "research_only": True,
            "purchase_approved": False}



def generate_official_research_shadow(manifest, generated_at_jst):
    """Run an explicitly *uncalibrated* shadow model on verified six-lane inputs.

    This output is ephemeral Action research evidence, not a Git forecast or
    purchase signal. No synthetic receipt clocks and no backdated prediction.
    Official 120-combination odds establish source completeness only and never
    reorder prediction probabilities by payout.
    """
    import hashlib
    import math
    from research_model import COUNTS, TICKETS
    from clean_four_modes import rank_modes

    generated = jst(generated_at_jst)
    cutoff = jst(manifest["cutoff_jst"])
    latest = max(jst(v["received_at_jst"]) for v in manifest["official_sources"].values())
    base_fields = {key: manifest[key] for key in
                   ("race_code", "cutoff_jst", "official_sources", "six_boat_inputs")}
    digest = hashlib.sha256(json.dumps(base_fields, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
    if (manifest.get("schema") != "OFFICIAL_REAUDITED_INPUT_MANIFEST_V1"
            or manifest.get("official_source_fields_reconstructed") is not True
            or manifest.get("formal_t12_certified") is not False
            or digest != manifest.get("input_sha256")
            or len(manifest["six_boat_inputs"]) != 6
            or set(manifest["official_sources"]) != {"racelist", "beforeinfo", "odds"}):
        raise ValueError("unverified_official_shadow_manifest")
    if latest > generated:
        return {"status": "source_receipt_after_requested_generation",
                "generated": False, "formal_t12_certified": False}
    if generated >= cutoff:
        return {"status": "t12_window_closed_no_shadow_generation",
                "generated": False, "formal_t12_certified": False}
    # All four numeric exhibition measurements come from the verified
    # beforeinfo original. Registration is identity, not a rank feature.
    # ST F/L flags are never silently interpreted as an ordinary fast start.
    strengths = {}
    for lane in manifest["six_boat_inputs"]:
        number, st = lane["lane"], lane["exhibition_st"]
        if (type(number) is not int or number not in range(1, 7)
                or number in strengths or type(st) is not str
                or not re.fullmatch(r"(?:[FL])?\.\d{1,2}|\d?\.\d{1,2}", st)):
            raise ValueError("unverified_official_shadow_exhibition")
        time = lane["exhibition_time"]
        tilt = lane["tilt"]
        course = lane["exhibition_course"]
        if (type(time) not in (int, float) or type(tilt) not in (int, float)
                or type(course) is not int or not math.isfinite(time)
                or not math.isfinite(tilt) or not 5 <= time <= 9
                or not -1 <= tilt <= 3 or course not in range(1, 7)):
            raise ValueError("unverified_official_shadow_reading")
        st_flagged = st.startswith(("F", "L"))
        st_seconds = float(st.lstrip("FL"))
        if not 0 <= st_seconds <= 0.99:
            raise ValueError("unverified_official_shadow_st")
        strengths[number] = (
            -4.0 * (time - 6.8)
            -1.5 * st_seconds
            +0.12 * (3.5 - course)
            -0.05 * abs(tilt)
            -(0.15 if st_flagged else 0.0)
        )
    if len(strengths) != 6 or len({x["exhibition_course"] for x in manifest["six_boat_inputs"]}) != 6:
        raise ValueError("unverified_official_shadow_six_courses")
    log_weights = [math.log(c + 0.5)
                   +0.85 * strengths[ticket[0]]
                   +0.35 * strengths[ticket[1]]
                   +0.15 * strengths[ticket[2]]
                   for ticket, c in zip(TICKETS, COUNTS)]
    peak = max(log_weights)
    weights = [math.exp(x - peak) for x in log_weights]
    denominator = sum(weights)
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError("official_shadow_probability_not_finite")
    board = [(ticket, weight / denominator) for ticket, weight in zip(TICKETS, weights)]
    modes = rank_modes(board)
    ranked = sorted(board, key=lambda x: (-x[1], x[0]))
    return {
        "schema": "OFFICIAL_SIX_LANE_RESEARCH_SHADOW_V1",
        "status": "research_shadow_generated_pre_t12",
        "generated": True, "generated_at_jst": generated.isoformat(),
        "t12_cutoff_jst": cutoff.isoformat(),
        "latest_official_source_received_jst": latest.isoformat(),
        "race_code": manifest["race_code"],
        "official_input_sha256": digest,
        "source_sha256_by_kind": {k: v["sha256"] for k, v in manifest["official_sources"].items()},
        "model_version": "official_exhibition_heuristic_shadow_v1_uncalibrated",
        "model_consumed_official_exhibition_fields": True,
        "model_consumed_official_odds_prices": False,
        "full_official_source_completeness_audited": True,
        "predictions": modes,
        "top_probability_order": ["-".join(map(str, ticket)) for ticket, _ in ranked[:10]],
        "formal_t12_certified": False,
        "independent_remote_first_seen_verified": False,
        "model_accuracy_verified": False,
        "purchase_approved": False,
        "research_only": True,
    }


def generate_timed_official_research_shadow(manifest, *, clock=None):
    """Attest *completion*, not merely start, before the research T-12 cutoff.

    Live audit uses an actual JST clock twice. A model that starts before T-12
    but finishes at/after T-12 must never be labeled pre-cutoff, even if it
    produced plausible tickets. No clock is synthesized or backdated.
    """
    from research_model import JST
    if clock is None:
        clock = lambda: datetime.now(JST)
    started = clock()
    if not isinstance(started, datetime) or started.utcoffset() != timedelta(hours=9):
        raise ValueError("invalid_research_shadow_start_clock")
    shadow = generate_official_research_shadow(manifest, started.isoformat())
    completed = clock()
    if (not isinstance(completed, datetime)
            or completed.utcoffset() != timedelta(hours=9) or completed < started):
        raise ValueError("invalid_research_shadow_completion_clock")
    if shadow.get("generated") is True:
        if completed >= jst(manifest["cutoff_jst"]):
            return {"status": "t12_window_closed_during_shadow_generation",
                    "generated": False, "formal_t12_certified": False,
                    "research_only": True, "purchase_approved": False}
        # Preserve one truthful completion timestamp; the privileged writer
        # independently replays and matches the same deterministic prediction.
        shadow["generated_at_jst"] = completed.isoformat()
    return shadow


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
                row["official_input_manifest"] = verified_official_input_manifest(dirs, audited)
                row["official_research_shadow"] = generate_timed_official_research_shadow(
                    row["official_input_manifest"])
                row["official_original_status"] = "three_originals_reaudited_research_only"
                row["latest_official_received_jst"] = audited["latest_original_received_jst"]
                row["forecast_statuses"] = {
                    name: snapshot_timing(
                        forecast_root / name, race, audited,
                        independent_beforeinfo_sha256=row["official_input_manifest"]
                            ["official_sources"]["beforeinfo"]["sha256"])
                    for name in ("prospective_predictions", "four_mode_forecasts",
                                 "scenario_forecasts", "v133_policy_forecasts")
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
                    for name in ("prospective_predictions", "four_mode_forecasts",
                                 "scenario_forecasts", "v133_policy_forecasts")
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
