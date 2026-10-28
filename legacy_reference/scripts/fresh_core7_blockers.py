#!/usr/bin/env python3
"""Read-only per-race CORE7 blocker evidence, not a formal eligibility grant."""
import collections
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
ymd = now.strftime("%Y%m%d")
root = Path("data")
status = json.loads((root / "model_status.json").read_text(encoding="utf-8"))
health_path = root / "health.json"
health = json.loads(health_path.read_text(encoding="utf-8")) if health_path.exists() else {}
counts = collections.Counter()
examples = {}
source_presence_gaps = collections.Counter()
for path in sorted((root / "races").glob(f"{ymd}-??-??.json")):
    try:
        race = json.loads(path.read_text(encoding="utf-8"))
        audit = race.get("source_audit") or {}
        model_input = race.get("current_model_input") or {}
        reasons = []
        deadline_text = (race.get("meta") or {}).get("deadline")
        try:
            hh, minute = (int(x) for x in deadline_text.split(":"))
            deadline = now.replace(hour=hh, minute=minute, second=0, microsecond=0)
            deadline_passed = deadline <= now
        except (ValueError, TypeError, AttributeError):
            deadline_passed = None
        deadline_bucket = ("deadline_passed" if deadline_passed is True else
                           "deadline_future" if deadline_passed is False else
                           "deadline_unknown")
        counts[deadline_bucket] += 1
        if model_input.get("core7_ready") is True:
            counts["core7_ready_on_saved_race"] += 1
            continue
        for role, key in (("race_card", "race_card"), ("stt", "stt"),
                          ("tkz", "tkz"), ("sui", "sui"),
                          ("original_exhibition", "original_exhibition")):
            item = audit.get(key) or {}
            if item.get("status") != "ok":
                reasons.append(f"{role}:{item.get('availability_reason') or item.get('status') or 'unknown'}")
        if not reasons:
            reasons.append("sources_ok_but_core7_not_ready")
        presence = model_input.get("source_presence") or {}
        if isinstance(presence, dict):
            for role in ("race_cards", "stt", "tkz", "sui", "original_exhibition"):
                if presence.get(role) is not True:
                    source_presence_gaps[role] += 1
        counts["not_ready_" + deadline_bucket] += 1
        for reason in reasons:
            counts[reason] += 1
            examples.setdefault(reason, path.stem)
        counts["races_not_core7_ready"] += 1
    except (ValueError, OSError, AttributeError, TypeError) as exc:
        counts["invalid_race_document"] += 1
        examples.setdefault("invalid_race_document", path.stem)
report = {
    "schema": "BOAT_EDGE_CORE7_READONLY_BLOCKERS_V1",
    "observed_at_jst": now.isoformat(timespec="seconds"),
    "model_status_updated_at": status.get("updated_at"),
    "model_source_rows": status.get("source_rows"),
    "model_core7": status.get("core7"),
    "health_updated_at": health.get("updated_at"),
    "urgent_15m": {
        "targets": health.get("beforeinfo_urgent_15m_targets"),
        "ok": health.get("beforeinfo_urgent_15m_ok"),
        "published_wait": health.get("beforeinfo_urgent_15m_published_wait"),
        "error": health.get("beforeinfo_urgent_15m_error"),
        "original_complete_initial": health.get("original_exhibition_urgent_15m_complete"),
        "original_missing_initial": health.get("original_exhibition_urgent_15m_missing"),
        "original_complete_post_enrichment": health.get("original_exhibition_post_enrichment_15m_complete"),
        "original_missing_post_enrichment": health.get("original_exhibition_post_enrichment_15m_missing"),
        "post_enrichment_targets": health.get("original_exhibition_post_enrichment_15m_targets"),
    },
    "urgent_and_post_enrichment_denominators_must_not_be_added": True,
    "saved_ready_count_may_differ_from_current_collector": True,
    "saved_race_counts": dict(sorted(counts.items())),
    "not_ready_source_presence_gaps": dict(sorted(source_presence_gaps.items())),
    "example_race_keys": examples,
    "counts_are_diagnostic_not_unique_missed_eligible_races": True,
    "source_audit_ok_is_not_full_core7_validation": True,
    "deadline_passed_is_not_proof_of_first_save_timing": True,
    "formal_unlock_authorized": False,
    "results_accessed": False,
}
Path("fresh_core7_blockers.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, sort_keys=True))
