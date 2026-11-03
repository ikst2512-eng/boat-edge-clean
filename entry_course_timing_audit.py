"""Research-only timing classification for entry/course challenger evidence.

An ordinary BoatraceCSV predeadline preview is often around T-5. It cannot
retroactively qualify a T-12 frozen comparison, even if received before the
actual betting deadline. A later-cutoff study is a different experiment.
"""
from datetime import datetime, timedelta
from typing import Mapping


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value)
        if t.utcoffset() is None:
            return None
        return t
    except ValueError:
        return None


def classify_course_timing(base: Mapping, preview: Mapping | None,
                           *, late_margin_minutes=2):
    """Report eligibility and do not generate forecasts or consume results."""
    if not isinstance(base, dict):
        return {"status": "invalid_baseline", "research_only": True,
                "eligible_for_t12_comparison": False}
    cutoff = _time(base.get("cutoff_jst"))
    deadline = _time(base.get("source_deadline_jst"))
    frozen = _time(base.get("generated_at"))
    if not cutoff or not deadline or not frozen or not frozen <= cutoff < deadline:
        return {"status": "invalid_baseline_timing", "research_only": True,
                "eligible_for_t12_comparison": False}
    if type(late_margin_minutes) not in (int, float) or not 0 < late_margin_minutes <= 5:
        return {"status": "invalid_late_window", "research_only": True,
                "eligible_for_t12_comparison": False}
    late_cutoff = deadline - timedelta(minutes=late_margin_minutes)
    if late_cutoff <= cutoff:
        return {"status": "invalid_late_window", "research_only": True,
                "eligible_for_t12_comparison": False}
    receipts = []
    sources = preview.get("sources", {}) if isinstance(preview, dict) else {}
    if preview and preview.get("status") == "ok":
        for kind in ("stt", "tkz"):
            raw = sources.get(kind)
            t = _time(raw.get("observed_at")) if isinstance(raw, dict) else None
            if t is None:
                return {"status": "preview_receipt_missing",
                        "eligible_for_t12_comparison": False, "research_only": True}
            receipts.append(t)
    if len(receipts) != 2:
        return {"status": "preview_unavailable", "eligible_for_t12_comparison": False,
                "research_only": True, "late_experiment_possible": False}
    last = max(receipts)
    if last >= deadline:
        status = "preview_after_deadline"
    elif last >= cutoff and last < late_cutoff:
        status = "preview_after_t12_late_research_only"
    elif last >= late_cutoff:
        status = "preview_too_late_for_late_research"
    else:
        status = "preview_available_before_t12"
    return {"status": status,
            "eligible_for_t12_comparison": last < cutoff,
            "late_experiment_possible": last < late_cutoff,
            "t12_cutoff": cutoff.isoformat(),
            "late_cutoff": late_cutoff.isoformat(),
            "last_preview_receipt": last.isoformat(),
            "baseline_frozen_at": frozen.isoformat(),
            "research_only": True,
            "formal_forecast_approved": False,
            "equal_information_comparison_verified": False}
