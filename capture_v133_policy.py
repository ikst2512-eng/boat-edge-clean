"""Forward-only, append-only V127/V133 3/10/12/(15|18|20) research receipts.

Consumes the EXISTING daily schedule and VERIFIED same-race card/beforeinfo.
Does not alter V2/legacy archives, historical results, outcomes, odds, or
provisionally frozen restored-scenario candidates. This is not proof of
independent remote first-seen or model accuracy; no retrospective generation.
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from legacy_scenario_engine import JST
from legacy_v133_reference_engine import v133_reference_preview

ROOT = Path(__file__).resolve().parent
SCHEMA = "CLEAN_V133_POINT_POLICY_PROSPECTIVE_RESEARCH_V1"
MODEL = "V127_V133_BALANCE12_HOLE15_18_20_REFERENCE_V2"
POLICY = "BALANCE12_WAVE15_18_20_V133_REFERENCE_V2"
EXPECTED = {"narrow": 3, "hit": 10, "balance": 12}
HOLE = (15, 18, 20)


def candidates(root, now):
    """Race schedule locates upcoming IDs ONLY; it never supplies forecast inputs."""
    folder = Path(root) / "schedule_snapshots"
    path = folder / (now.strftime("%Y%m%d") + ".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 150000:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("date", "")).replace("-", "") != now.strftime("%Y%m%d"):
        return []
    upcoming = []
    for venue in data.get("venues", []):
        jcd = str(venue.get("jcd", "")).zfill(2)
        if not re.fullmatch(r"0[1-9]|1[0-9]|2[0-4]", jcd):
            continue
        for race in venue.get("races", []):
            rno = race.get("race_no")
            hhmm = race.get("deadline")
            if (type(rno) is not int or not 1 <= rno <= 12
                    or not isinstance(hhmm, str)
                    or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", hhmm)):
                continue
            deadline = datetime.strptime(
                now.strftime("%Y%m%d") + hhmm, "%Y%m%d%H:%M").replace(tzinfo=JST)
            remain = (deadline - now).total_seconds()
            if 180 <= remain <= 1080:
                code = f"{now:%Y%m%d}{jcd}{rno:02d}"
                upcoming.append((deadline, code))
    return [(code, deadline) for deadline, code in sorted(set(upcoming))]


def _timestamp(text):
    value = datetime.fromisoformat(text)
    if value.utcoffset() != timedelta(hours=9):
        raise ValueError("unverified_jst_receipt")
    return value


def verify_snapshot(path, now=None):
    """Validate a *new* predeadline snapshot before each commit or push."""
    now = datetime.now(JST) if now is None else now
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(hours=9):
        raise ValueError("jst_clock_required")
    path = Path(path)
    if (path.is_symlink() or not re.fullmatch(r"20\d{10}\.json", path.name)
            or path.stat().st_size > 55000):
        raise ValueError("invalid_v133_snapshot_path")
    code = path.stem
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("schema") != SCHEMA or data.get("race_code") != code
            or data.get("model_version") != MODEL
            or data.get("selection_policy") != POLICY
            or data.get("status") != "predeadline_v133_policy_research_frozen"
            or data.get("formal") is not False or data.get("calibrated") is not False
            or data.get("production_buy_approved") is not False
            or data.get("first_remote_add_verified") is not False
            or data.get("accuracy_improvement_proven") is not False
            or data.get("historical_predictions_reconstructed") is not False
            or data.get("v2_archive_untouched") is not True):
        raise ValueError("invalid_v133_research_identity")
    when = _timestamp(data["generated_at_jst"])
    deadline = _timestamp(data["deadline_jst"])
    if (not when <= now < deadline - timedelta(seconds=90)
            or not when < deadline - timedelta(seconds=120)
            or deadline.strftime("%Y%m%d") != code[:8]):
        raise ValueError("v133_publication_window_closed")
    audit = data.get("source_audit")
    if not isinstance(audit, dict):
        raise ValueError("v133_missing_source_audit")
    for name in ("race_card", "beforeinfo"):
        record = audit.get(name)
        if not isinstance(record, dict) or record.get("status") != "ok":
            raise ValueError("v133_missing_verified_" + name)
        timestamp = _timestamp(record["fetched_at"])
        if timestamp > when or timestamp >= deadline:
            raise ValueError("source_received_after_v133_generation")
    sha = audit["race_card"].get("sha256")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", str(sha or "")):
        raise ValueError("v133_source_digest_missing")
    if sha != data.get("source_racecard_sha256"):
        raise ValueError("v133_racecard_sha_mismatch")
    modes = data.get("modes")
    if not isinstance(modes, dict) or not set(EXPECTED).issubset(modes):
        raise ValueError("v133_missing_modes")
    if set(modes) not in (set(EXPECTED) | {"hole"}, set(EXPECTED) | {"hole", "tail"}):
        raise ValueError("v133_unknown_modes")
    counts = dict(EXPECTED)
    count_hole = (modes["hole"] or {}).get("count")
    if count_hole not in HOLE:
        raise ValueError("v133_wrong_hole_size")
    counts["hole"] = count_hole
    if "tail" in modes:
        counts["tail"] = 10
    for mode, count in counts.items():
        entry = modes[mode]
        rows = entry.get("tickets") if isinstance(entry, dict) else None
        if not isinstance(rows, list) or len(rows) != count or entry.get("count") != count:
            raise ValueError("v133_wrong_ticket_count_" + mode)
        combos = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("v133_invalid_ticket")
            combo = row.get("combo")
            confidence = row.get("p")
            if (not isinstance(combo, str) or
                    not re.fullmatch(r"[1-6]-[1-6]-[1-6]", combo) or
                    len(set(combo.split("-"))) != 3 or
                    isinstance(confidence, bool) or
                    type(confidence) not in (int, float) or
                    not 0 <= confidence <= 100):
                raise ValueError("v133_invalid_ticket")
            combos.append(combo)
        if len(set(combos)) != count:
            raise ValueError("v133_duplicate_ticket")
    if data.get("race_code") != code:
        raise ValueError("v133_wrong_race")
    return code


def collect(root=ROOT, now=None, card_loader=None, max_races=8):
    injected = now is not None
    now = datetime.now(JST) if now is None else now
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(hours=9):
        raise ValueError("jst_clock_required")
    if type(max_races) is not int or not 1 <= max_races <= 24:
        raise ValueError("invalid_v133_candidate_limit")
    if card_loader is None:
        from clean_racecard import racecard
        card_loader = racecard
    root = Path(root)
    dest = root / "v133_policy_forecasts"
    saved, rejected = [], {}
    for code, deadline in candidates(root, now)[:max_races]:
        target = dest / (code + ".json")
        if target.exists() or target.is_symlink():
            continue
        try:
            card = card_loader(code[:8], code[8:10], str(int(code[10:12])))
            if not isinstance(card, dict) or card.get("race_key") != (
                    code[:8] + "-" + code[8:10] + "-" + code[10:12]):
                raise ValueError("v133_wrong_race_card")
            # Real network requests consume time: sample the clock AFTER fetch.
            generated = now if injected else datetime.now(JST)
            if (deadline - generated).total_seconds() < 180:
                raise ValueError("v133_too_close_to_deadline")
            output = v133_reference_preview(card, now=generated)
            if (output.get("race_code") != code or
                    output.get("deadline_jst") != deadline.isoformat() or
                    output.get("model_version") != MODEL or
                    output.get("selection_policy") != POLICY):
                raise ValueError("v133_wrong_output_identity")
            record = dict(output,
                schema=SCHEMA,
                status="predeadline_v133_policy_research_frozen",
                generated_at_jst=generated.isoformat(),
                v2_archive_untouched=True,
                # Do not promote local generation to a remote-first receipt.
                first_remote_add_verified=False,
                formal=False, calibrated=False,
                accuracy_improvement_proven=False,
                production_buy_approved=False,
                historical_predictions_reconstructed=False,
            )
            # Store exact feature-source receipt metadata consumed by this race.
            path_temp = dest / (code + ".json")
            dest.mkdir(parents=True, exist_ok=True)
            with path_temp.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            verify_snapshot(path_temp, now=generated)
            saved.append(code)
        except (OSError, ValueError, TypeError, KeyError) as err:
            # Invalid local candidates are never published; only the module's
            # own new file can be removed after an unsuccessful validation.
            if target.exists() and not target.is_symlink() and code not in saved:
                target.unlink()
            key = str(err)[:100] or type(err).__name__
            rejected[key] = rejected.get(key, 0) + 1
    return {"date_jst": now.strftime("%Y%m%d"), "saved": saved,
            "rejected": rejected, "model": MODEL,
            "formal": False, "first_remote_add_verified": False}


if __name__ == "__main__":
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True))
