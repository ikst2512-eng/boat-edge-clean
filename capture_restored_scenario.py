"""Forward-only, write-once restored scenario forecast research captures.

This is the original score/head-world preview with an explicitly uncalibrated
120-way extension. It does not supersede immutable V2 comparator archives,
does not certify T-12 and never reconstructs a closed race.
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from legacy_scenario_engine import JST, MODEL_VERSION, restored_scenario_preview

ROOT = Path(__file__).resolve().parent
SCHEMA = "CLEAN_RESTORED_SCENARIO_FORWARD_CAPTURE_V1"


def collect(root=ROOT, now=None, card_loader=None, max_races=8):
    if card_loader is None:
        from clean_racecard import racecard
        card_loader = racecard
    injected_clock = now is not None
    now = datetime.now(JST) if now is None else now
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(hours=9):
        raise ValueError("jst_clock_required")
    if type(max_races) is not int or not 1 <= max_races <= 24:
        raise ValueError("bad_candidate_limit")
    today = now.strftime("%Y%m%d")
    originals = root / "four_mode_forecasts"
    destination = root / "scenario_forecasts"
    saved = []
    excluded = {}
    attempted = 0
    for source in sorted(originals.glob(today + "*.json")):
        if attempted >= max_races:
            break
        code = source.stem
        if (source.is_symlink() or not re.fullmatch(r"20\d{10}", code)
                or int(code[8:10]) not in range(1, 25)
                or int(code[10:12]) not in range(1, 13)
                or source.stat().st_size > 30000):
            continue
        target = destination / (code + ".json")
        if target.is_symlink() or target.exists():
            continue
        try:
            base = json.loads(source.read_text(encoding="utf-8"))
            if base.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1" or base.get("race_code") != code:
                continue
            deadline = datetime.fromisoformat(base["deadline_jst"])
            remaining = (deadline - now).total_seconds()
            # The existing 15-minute collection cadence can visit this safe
            # near-deadline window once. Do not freeze a morning-only estimate.
            if deadline.utcoffset() != timedelta(hours=9) or not 180 <= remaining <= 1080:
                continue
            attempted += 1
            card = card_loader(today, code[8:10], str(int(code[10:12])))
            if type(card) is not dict or card.get("race_key") != (
                    today + "-" + code[8:10] + "-" + code[10:12]):
                raise ValueError("wrong_race_card_identity")
            source_audit = card.get("source_audit")
            if type(source_audit) is not dict:
                raise ValueError("missing_source_audit")
            before_audit = source_audit.get("beforeinfo")
            if type(before_audit) is not dict or before_audit.get("status") != "ok":
                raise ValueError("verified_six_exhibition_required")
            generated = now if injected_clock else datetime.now(JST)
            # Fail closed if HTTP consumption takes the race past the safety
            # window. The caller clock is sampled AFTER the network fetch.
            if not 120 <= (deadline-generated).total_seconds():
                raise ValueError("generation_too_late")
            data = restored_scenario_preview(card, now=generated)
            if (data.get("model_version") != MODEL_VERSION or
                    data.get("race_code") != code or
                    data.get("observed_exhibition_only") is not True or
                    data.get("formal") is not False or
                    data.get("production_buy_approved") is not False):
                raise ValueError("unverified_scenario_output")
            record = {
                **data,
                "schema": SCHEMA,
                "status": "predeadline_frozen_scenario_research",
                "generated_at_jst": generated.isoformat(),
                "source_audit": source_audit,
                "v2_archive_untouched": True,
                "first_remote_add_verified": False,
                "formal": False,
                "calibrated": False,
                "production_buy_approved": False,
            }
            destination.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            saved.append(code)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            label = str(exc)[:90] or type(exc).__name__
            excluded[label] = excluded.get(label, 0) + 1
    return {"date_jst": today, "attempted": attempted, "new_saved": saved,
            "excluded": excluded, "formal": False, "source_model": MODEL_VERSION}



def verify_snapshot(path, now=None):
    """Fail closed on a candidate not safe to commit/push to remote main."""
    now = datetime.now(JST) if now is None else now
    path = Path(path)
    if path.is_symlink() or not re.fullmatch(r"20\d{10}\.json", path.name):
        raise ValueError("invalid_scenario_path")
    if path.stat().st_size > 30000:
        raise ValueError("scenario_snapshot_too_large")
    data = json.loads(path.read_text(encoding="utf-8"))
    code = path.stem
    if (data.get("schema") != SCHEMA or data.get("race_code") != code or
            data.get("model_version") != MODEL_VERSION or
            data.get("status") != "predeadline_frozen_scenario_research" or
            data.get("formal") is not False or data.get("calibrated") is not False or
            data.get("first_remote_add_verified") is not False or
            data.get("production_buy_approved") is not False or
            data.get("observed_exhibition_only") is not True or
            data.get("v2_archive_untouched") is not True):
        raise ValueError("invalid_scenario_identity_or_flags")
    generated = datetime.fromisoformat(data["generated_at_jst"])
    deadline = datetime.fromisoformat(data["deadline_jst"])
    if (now.utcoffset() != timedelta(hours=9) or
            generated.utcoffset() != timedelta(hours=9) or
            deadline.utcoffset() != timedelta(hours=9) or
            not generated < deadline - timedelta(seconds=120) or
            not now < deadline - timedelta(seconds=90)):
        raise ValueError("scenario_predeadline_publish_window_closed")
    source = data.get("source_audit")
    if not isinstance(source, dict):
        raise ValueError("missing_full_source_audit")
    for key in ("race_card", "beforeinfo"):
        record = source.get(key)
        if not isinstance(record, dict) or record.get("status") != "ok":
            raise ValueError("missing_verified_" + key)
        received = datetime.fromisoformat(record["fetched_at"])
        if received.utcoffset() != timedelta(hours=9) or received > generated:
            raise ValueError("source_received_after_scenario_generation")
    if source["race_card"].get("sha256") != data.get("source_racecard_sha256"):
        raise ValueError("scenario_racecard_sha_mismatch")
    expected = {"narrow":5,"hit":10,"balance":16,"hole":22}
    modes = data.get("modes")
    if not isinstance(modes, dict) or set(modes) != set(expected):
        raise ValueError("scenario_modes_missing")
    for mode, count in expected.items():
        rows = modes[mode].get("tickets")
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError("scenario_ticket_count_changed")
        combos = [r.get("combo") for r in rows if isinstance(r, dict)]
        if (len(combos) != count or len(set(combos)) != count or
                any(not isinstance(t,str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]",t) or
                    len(set(t.split("-"))) != 3 for t in combos)):
            raise ValueError("scenario_ticket_invalid")
    return code


if __name__ == "__main__":
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
