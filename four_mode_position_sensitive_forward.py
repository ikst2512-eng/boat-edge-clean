"""Separate, result-LAST forward comparator for the position-sensitive shadow.

No scheduled capture, no automatic publishing, no outcome leakage into selection.
Locally frozen candidates do NOT prove independent first remote receipt.
Do not use this output for formal certification or live betting.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import shadow_modes

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "research/four_mode_position_sensitive_forward_protocol_20261108.json"
PROTOCOL_BLOB_SHA1 = "9559b4f8b95d5a0cb1a7feaf700494566dcaba94"
SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_LOCAL_FREEZE_V1"
DATE_START = "2026-11-09T00:00:00+09:00"
DATE_END = "2026-12-31T23:59:59+09:00"
MODES = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TOPS = (1, 3, 5, 10)
CODE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
JST = timezone(timedelta(hours=9))
FORBIDDEN = {"finish_order", "winning_ticket", "result", "results",
             "payout", "confirmed_at_jst", "actual_hit_rate_pct"}


def _blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _clock(value):
    try:
        d = datetime.fromisoformat(value) if isinstance(value, str) else value
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_clock") from exc
    if type(d) is not datetime or d.utcoffset() != timedelta(hours=9):
        raise ValueError("clock_must_be_JST")
    return d


def protocol():
    raw = PROTOCOL.read_bytes()
    if _blob_sha1(raw) != PROTOCOL_BLOB_SHA1:
        raise ValueError("preregistration_modified")
    p = json.loads(raw)
    if (p.get("schema") != "FOUR_MODE_POSITION_SENSITIVE_FORWARD_PREREGISTRATION_V1"
            or p.get("registered_jst_date") != "2026-11-08"
            or p.get("eligible_deadline_start_jst") != DATE_START
            or p.get("eligible_deadline_end_jst") != DATE_END
            or p.get("pilot_races") != 300 or p.get("confirmation_races") != 300
            or p.get("compare_counts") != MODES
            or p.get("factor_second_beta") != 0.5
            or p.get("factor_third_beta") != 0.25
            or p.get("promotion_allowed") is not False):
        raise ValueError("preregistration_invalid")
    for filename, key in (
        ("four_mode_position_sensitive_shadow.py", "candidate_selector_git_blob_sha1"),
        ("research_model.py", "original_model_git_blob_sha1"),
        ("clean_four_modes.py", "mode_selector_git_blob_sha1"),
    ):
        expected = p.get(key)
        if not isinstance(expected, str) or not SHA40.fullmatch(expected):
            raise ValueError("selector_identity_missing")
        actual = _blob_sha1((ROOT / filename).read_bytes())
        if actual != expected:
            raise ValueError("selector_dependency_modified")
    return p


def _pre_result(original_bytes, code, p):
    """Authenticate exact stored V2 input bytes by recalculating EVERY ticket."""
    if type(original_bytes) is not bytes or not 0 < len(original_bytes) < 30001:
        raise ValueError("invalid_original_bytes")
    raw = json.loads(original_bytes)
    if (type(raw) is not dict or raw.get("race_code") != code or
            not CODE.fullmatch(code) or
            raw.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or
            raw.get("model_version") != p["baseline_model"] or
            raw.get("validated") is not False or
            raw.get("target_rates_not_proven") is not True or
            set(raw) & FORBIDDEN):
        raise ValueError("invalid_or_postrace_original")
    d = _clock(raw.get("deadline_jst"))
    generated = _clock(raw.get("generated_at_jst"))
    title = _clock(raw.get("source_title_received_jst"))
    cards = _clock(raw.get("source_cards_received_jst"))
    if (not (_clock(DATE_START) <= d <= _clock(DATE_END)) or
            d.strftime("%Y%m%d") != code[:8] or
            max(title, cards) > generated or
            generated >= d - timedelta(minutes=12)):
        raise ValueError("original_chronology_or_date_invalid")
    rates = raw.get("input_national_win_rates")
    if (type(rates) is not list or len(rates) != 6 or
            any(type(r) not in (float, int) or not math.isfinite(r)
                or not 0 < r <= 10 for r in rates)):
        raise ValueError("invalid_rates")
    baseline = rank_modes(probabilities(rates))
    for mode in MODES:
        saved = raw.get("modes", {}).get(mode, {}).get("tickets")
        if (type(saved) is not list or len(saved) != MODES[mode] or
                [(x.get("combo"), x.get("p")) for x in saved] !=
                [(x["combo"], x["p"]) for x in baseline[mode]["tickets"]]):
            raise ValueError("original_ticket_reproduction_failed")
    return raw, d, generated, baseline


def freeze_candidate(original_bytes, frozen_at_jst):
    """Generate candidate BEFORE result using exact original bytes only.

    Returned artifact is a LOCAL snapshot; no independent publication proof.
    """
    p = protocol()
    data = json.loads(original_bytes)
    code = data.get("race_code") if type(data) is dict else None
    raw, deadline, original_at, baseline = _pre_result(original_bytes, code, p)
    frozen = _clock(frozen_at_jst)
    if not original_at < frozen < deadline - timedelta(minutes=12):
        raise ValueError("not_frozen_strictly_before_T12")
    candidate = shadow_modes(raw["input_national_win_rates"])["modes"]
    out = {
        "schema": SCHEMA, "race_code": code, "status": "local_only_unpublished",
        "research_only": True, "formal": False,
        "production_forecast_changed": False,
        "candidate_first_remote_receipt_verified": False,
        "protocol_git_blob_sha1": PROTOCOL_BLOB_SHA1,
        "candidate_selector_git_blob_sha1": p["candidate_selector_git_blob_sha1"],
        "original_forecast_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "original_generated_at_jst": original_at.isoformat(),
        "deadline_jst": deadline.isoformat(),
        "candidate_locally_frozen_at_jst": frozen.isoformat(),
        "baseline": {m: [v["combo"] for v in baseline[m]["tickets"]] for m in MODES},
        "candidate": {m: [v["combo"] for v in candidate[m]["tickets"]] for m in MODES},
    }
    return out


def _verify_snapshot(s, original_bytes, p):
    if (type(s) is not dict or set(s) & FORBIDDEN or
            s.get("schema") != SCHEMA or
            s.get("status") != "local_only_unpublished" or
            s.get("research_only") is not True or
            s.get("formal") is not False or
            s.get("production_forecast_changed") is not False or
            s.get("candidate_first_remote_receipt_verified") is not False or
            s.get("protocol_git_blob_sha1") != PROTOCOL_BLOB_SHA1 or
            s.get("candidate_selector_git_blob_sha1") !=
            p["candidate_selector_git_blob_sha1"]):
        raise ValueError("invalid_or_forged_local_snapshot")
    code = s.get("race_code")
    if (not isinstance(code, str) or not CODE.fullmatch(code) or
            not isinstance(s.get("original_forecast_sha256"), str) or
            not SHA64.fullmatch(s["original_forecast_sha256"]) or
            hashlib.sha256(original_bytes).hexdigest() != s["original_forecast_sha256"]):
        raise ValueError("source_blob_changed")
    raw, deadline, original_at, baseline = _pre_result(original_bytes, code, p)
    local_at = _clock(s.get("candidate_locally_frozen_at_jst"))
    if (s.get("deadline_jst") != deadline.isoformat() or
            s.get("original_generated_at_jst") != original_at.isoformat() or
            not original_at < local_at < deadline - timedelta(minutes=12)):
        raise ValueError("unsafe_candidate_clock")
    expected = shadow_modes(raw["input_national_win_rates"])["modes"]
    for mode, size in MODES.items():
        old = s.get("baseline", {}).get(mode)
        new = s.get("candidate", {}).get(mode)
        if (type(old) is not list or type(new) is not list or
                old != [x["combo"] for x in baseline[mode]["tickets"]] or
                new != [x["combo"] for x in expected[mode]["tickets"]] or
                len(old) != size or len(new) != size or
                len(set(new)) != size):
            raise ValueError("candidate_or_original_selector_drift")
    return {"code": code, "deadline": deadline,
            "baseline": s["baseline"], "candidate": s["candidate"]}


def _outcome(value, code, deadline):
    if value is None:
        return "pending", None
    try:
        if type(value) is not dict or value.get("race_code") != code or value.get("status") != "confirmed":
            return "invalid", None
        confirmed = _clock(value.get("confirmed_at_jst"))
        collected = _clock(value.get("collected_at_jst"))
        expected_url = ("https://boatracecsv.github.io/data/results/realtime/" +
                        code[:4] + "/" + code[4:6] + "/" + code[6:8] + ".csv")
        finish = value.get("finish_order")
        if (confirmed <= deadline or collected < confirmed or
                value.get("source_url") != expected_url or
                not isinstance(value.get("source_sha256"), str) or
                not SHA64.fullmatch(value["source_sha256"]) or
                type(finish) is not list or len(finish) != 3 or
                any(type(x) is not int or not 1 <= x <= 6 for x in finish) or
                len(set(finish)) != 3):
            return "invalid", None
    except (ValueError, TypeError):
        return "invalid", None
    return "confirmed", "-".join(map(str, finish))


def compare_reference(frozen_snapshots, exact_original_bytes, outcomes):
    """Validates ENTIRE candidate roster before reading ANY outcome.

    A supplied ledger is not a complete independent Actions/first-remote
    receipt inventory, so this scorer is ALWAYS reference-only even if hits.
    """
    p = protocol()
    if (type(frozen_snapshots) is not list or type(exact_original_bytes) is not dict or
            not hasattr(outcomes, "get")):
        raise ValueError("invalid_inputs")
    rows = {}
    for s in frozen_snapshots:
        code = s.get("race_code") if type(s) is dict else None
        if code in rows:
            raise ValueError("duplicate_candidate_race")
        if code not in exact_original_bytes:
            raise ValueError("missing_immutable_original")
        row = _verify_snapshot(s, exact_original_bytes[code], p)
        rows[code] = row
    ordered = sorted(rows.values(), key=lambda x: (x["deadline"], x["code"]))[:600]
    stats = {phase: {mode: {str(n): {
        "baseline": 0, "candidate": 0, "gained": 0, "lost": 0
    } for n in TOPS} for mode in MODES} for phase in ("pilot", "confirmation")}
    confirmed_count = Counter()
    pending = []
    invalid = []
    for index, row in enumerate(ordered):
        code = row["code"]
        result_status, finish = _outcome(outcomes.get(code), code, row["deadline"])
        if result_status == "pending":
            pending.append(code)
            continue
        if result_status == "invalid":
            invalid.append(code)
            continue
        phase = "pilot" if index < 300 else "confirmation"
        confirmed_count[phase] += 1
        for mode in MODES:
            for top in TOPS:
                base = finish in row["baseline"][mode][:top]
                candidate = finish in row["candidate"][mode][:top]
                s = stats[phase][mode][str(top)]
                s["baseline"] += int(base)
                s["candidate"] += int(candidate)
                s["gained"] += int(candidate and not base)
                s["lost"] += int(base and not candidate)
    for phase in stats:
        for mode in stats[phase]:
            for top in TOPS:
                s = stats[phase][mode][str(top)]
                s["reference_denominator"] = confirmed_count[phase]
                if s["candidate"] - s["baseline"] != s["gained"] - s["lost"]:
                    raise ValueError("paired_result_partition_error")
    return {
        "schema": "FOUR_MODE_POSITION_SENSITIVE_REFERENCE_SCORE_V1",
        "status": "reference_only_unverified_first_remote_receipt",
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "candidate_first_remote_receipt_verified": False,
        "complete_capture_inventory_verified": False,
        "official_T12_beforeinfo_six_and_odds_120_verified": False,
        "eligible_frozen_candidate_slots": len(ordered),
        "pilot_reserved_slots": min(len(ordered), 300),
        "confirmation_reserved_slots": max(0, len(ordered) - 300),
        "confirmed_result_counts": dict(confirmed_count),
        "pending_race_codes": pending, "invalid_result_race_codes": invalid,
        "by_phase_mode_topn": stats,
        "warning": "Reference-only; supplied local freeze clocks and SHA are NOT first remote receipt. "
                   "Missing outcomes reserve their slot. Nothing here authorizes model adoption."
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze-original", type=Path,
                    help="PREDEADLINE freeze from one already-published exact original JSON")
    ap.add_argument("--output", type=Path,
                    help="Optional exclusive-create local research-only output (never a remote receipt)")
    args = ap.parse_args()
    if args.freeze_original is None:
        print(json.dumps({
            "status": "preregistered_candidate_not_running",
            "formal": False, "eligible_frozen_candidate_slots": 0,
            "first_remote_receipt_verified": False, "promotion_allowed": False,
        }))
        return
    if args.freeze_original.is_symlink() or not args.freeze_original.is_file():
        raise ValueError("untrusted_original_path")
    snapshot = freeze_candidate(args.freeze_original.read_bytes(), datetime.now(JST))
    content = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(content)
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
