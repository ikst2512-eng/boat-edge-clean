"""Research-only comparison of frozen original/result JSON with current public CSV.

Read only. Neither recoveries nor source rows are written into confirmed_results.
Never score a public CSV row as a formally certified race. A current CSV blob
can be appended after a persisted result: historical raw SHA mismatch alone
is NOT proof of tampering or equal to a verified first result receipt.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from collect_clean_results import (
    BASE, JST, build_records, confirmed_record_is_usable, source_gap_reasons
)
from four_mode_nov05_08_daily_reference_audit import DAYS, ROOT, audit


def _clock(value):
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_clock") from exc
    if dt.utcoffset() is None:
        raise ValueError("timezone_missing")
    return dt


def evaluate(root, raw_by_day, *, observed_at=None, days=DAYS):
    root = Path(root)
    days = tuple(days)
    if (not isinstance(raw_by_day, dict) or set(raw_by_day) != set(days)
            or len(set(days)) != len(days)):
        raise ValueError("incomplete_raw_source_roster")
    now = observed_at or datetime.now(JST)
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(hours=9):
        raise ValueError("observation_not_JST")
    reference = audit(root, days)
    if any(x["excluded_count"] for x in reference["by_day"].values()):
        raise ValueError("saved_forecast_or_result_excluded_manual_review")
    summary = {}
    overall = Counter()
    for day in days:
        raw = raw_by_day[day]
        if type(raw) is not bytes or not 0 < len(raw) <= 2_000_000:
            raise ValueError("missing_or_unsafe_raw_csv:" + day)
        # Collector's own duplicate, finish, and source-clock gates.
        eligible = build_records(day, raw, now)
        pending = reference["by_day"][day]["pending_result_codes"]
        reasons = source_gap_reasons(day, raw, pending, collected_at=now)
        breakdown = Counter()
        lists = {}
        for code in pending:
            reason = reasons[code]
            if reason == "row_present_requires_review" and code in eligible:
                forecast = json.loads((root / "four_mode_forecasts" /
                                       (code + ".json")).read_bytes())
                source_clock = _clock(eligible[code]["confirmed_at_jst"])
                cutoff = _clock(forecast["deadline_jst"])
                category = ("valid_source_three_finish_unpersisted"
                            if source_clock > cutoff
                            else "source_clock_not_after_deadline")
            elif reason == "invalid_or_unfinished_finish":
                category = "invalid_or_unfinished_finish_not_scoreable"
            elif reason == "not_in_published_csv":
                category = "not_in_published_csv"
            else:
                category = "source_not_eligible_or_timestamp_unverified"
            breakdown[category] += 1
            lists.setdefault(category, []).append(code)
        matched = 0
        disagreements = []
        digest_changed = 0
        for path in sorted((root / "four_mode_forecasts").glob(day + "*.json")):
            code = path.stem
            if code in pending:
                continue
            result_path = root / "confirmed_results" / (code + ".json")
            if not confirmed_record_is_usable(result_path, code):
                raise ValueError("result_trust_changed_since_reference:" + code)
            stored = json.loads(result_path.read_bytes())
            upstream = eligible.get(code)
            if (upstream is None
                    or stored["finish_order"] != upstream["finish_order"]
                    or _clock(stored["confirmed_at_jst"]) !=
                       _clock(upstream["confirmed_at_jst"])):
                disagreements.append(code)
                continue
            matched += 1
            if stored["source_sha256"] != hashlib.sha256(raw).hexdigest():
                digest_changed += 1
        expected = reference["by_day"][day]
        if (matched + len(disagreements) != expected["evaluated"]
                or sum(breakdown.values()) != expected["pending_result_count"]):
            raise AssertionError("raw_row_or_pending_denominator_mismatch")
        summary[day] = {
            "raw_url": BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv",
            "current_raw_sha256": hashlib.sha256(raw).hexdigest(),
            "current_raw_bytes": len(raw),
            "saved_result_rows_matched_current_csv": matched,
            "saved_result_rows_disagree_or_not_present": disagreements,
            "stored_hash_differs_from_current_appended_csv": digest_changed,
            "pending_classification_counts": dict(sorted(breakdown.items())),
            "pending_codes_by_class": {k: sorted(v) for k, v in sorted(lists.items())},
        }
        overall.update(breakdown)
        overall["saved_result_rows_matched_current_csv"] += matched
        overall["saved_result_rows_disagree_or_not_present"] += len(disagreements)
    return {
        "schema": "FOUR_MODE_ORIGINAL_CURRENT_PUBLIC_RESULT_CSV_RESEARCH_AUDIT_V1",
        "status": "current_upstream_row_observation_reference_only",
        "observed_at_jst": now.isoformat(),
        "by_day": summary,
        "totals": dict(sorted(overall.items())),
        "frozen_original_result_reference": reference["totals"],
        "current_csv_is_not_official_result_provenance": True,
        "current_raw_hash_not_historical_first_result_sha": True,
        "candidate_not_scored": True,
        "formal": False, "formal_count": 0,
        "prospective_candidate_pairs": 0,
        "model_improvement_proven": False, "model_promotion_allowed": False,
        "warning": "Current third-party CSV row is not proof of official T-12, independent first remote receipt, immutable historical raw bytes, or prospective candidate improvement. Never write or backfill pending forecasts/results in this research tool.",
    }


def fetch_csv(days):
    out = {}
    for day in days:
        target = BASE + f"{day[:4]}/{day[4:6]}/{day[6:]}.csv"
        req = Request(target, headers={"User-Agent": "boat-edge-four-mode-readonly-source-audit/1.0"})
        with urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise ValueError("upstream_non_200:" + day)
            raw = response.read(2_000_001)
        if not raw or len(raw) > 2_000_000:
            raise ValueError("upstream_empty_or_oversize:" + day)
        out[day] = raw
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--fetch", action="store_true",
                        help="Read current public source CSV, without writing any files")
    parser.add_argument("--source-dir", type=Path,
                        help="Offline CSV directory containing YYYYMMDD.csv for each day")
    args = parser.parse_args()
    if args.fetch == (args.source_dir is not None):
        parser.error("exactly one of --fetch or --source-dir required")
    if args.fetch:
        raws = fetch_csv(DAYS)
    else:
        raws = {day: (args.source_dir / (day + ".csv")).read_bytes()
                for day in DAYS}
    print(json.dumps(evaluate(args.root, raws), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
