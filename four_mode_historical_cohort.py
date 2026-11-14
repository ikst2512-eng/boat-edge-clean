"""Run bounded, reproducible historical four-mode research on real archived files."""
import json
import re
import hashlib
from pathlib import Path
from four_mode_research_batch import summarize, MODES
from four_mode_frozen_diagnostic import compare_race
from four_mode_archive_api import archived_four_modes

ROOT = Path(__file__).resolve().parent

def summarize_group(codes, root, include_per_race=False):
    # summarize accepts max 30 codes; keep every subgroup bounded.
    chunks = [summarize(codes[i:i+30], root=root) for i in range(0, len(codes), 30)]
    comparable = sum(x["historical_comparable"] for x in chunks)
    hits = {m: {f"top{n}": sum(x["modes"][m]["topn_hits"][f"top{n}"] for x in chunks)
                for n in (1,3,5,10)} for m in MODES}
    report = {"requested": len(codes), "historical_comparable": comparable,
              "topn_hits": hits, "formal": False}
    if include_per_race:
        report["per_race"] = [row for chunk in chunks for row in chunk["per_race"]]
        if len(report["per_race"]) != comparable:
            raise ValueError("per_race_denominator_mismatch")
        # Aggregate the complete six-pair matrix from disjoint <=30-race
        # chunks; reconcile all paired totals against the identical cohort.
        pairs = {}
        for name in chunks[0]["pairwise_topn"] if chunks else ():
            left, right = name.split("_vs_")
            topn = {}
            for n in (1, 3, 5, 10):
                key = f"top{n}"
                counts = {tag: sum(chunk["pairwise_topn"][name]["topn"][key][tag]
                                   for chunk in chunks)
                          for tag in ("both", "left_only", "right_only", "neither")}
                if (sum(counts.values()) != comparable
                        or counts["both"] + counts["left_only"] != hits[left][key]
                        or counts["both"] + counts["right_only"] != hits[right][key]):
                    raise ValueError("pairwise_denominator_mismatch")
                counts["evaluated"] = comparable
                counts["net_additional_hits"] = counts["right_only"] - counts["left_only"]
                counts["net_percentage_points"] = (
                    round(100 * counts["net_additional_hits"] / comparable, 2)
                    if comparable else None)
                topn[key] = counts
            pairs[name] = {"evaluated": comparable, "topn": topn,
                           "formal": False}
        report["pairwise_topn"] = pairs
    return report


def run(root=ROOT, limit=120):
    root = Path(root)
    forecast_dir, results_dir = root / "four_mode_forecasts", root / "confirmed_results"
    available = sorted(p.stem for p in forecast_dir.glob("20??????????.json")
                       if re.fullmatch(r"20[0-9]{10}", p.stem)
                       and (results_dir / p.name).is_file())
    # Rotate through both dates and venues, avoiding early venue/race-order bias.
    # All choices are deterministic and based only on immutable filenames.
    by_day_venue = {}
    for code in available:
        by_day_venue.setdefault(code[:8], {}).setdefault(code[8:10], []).append(code)
    by_date = {}
    for day, venues in by_day_venue.items():
        selected = []
        offset = 0
        while True:
            batch = [venues[venue][offset] for venue in sorted(venues)
                     if offset < len(venues[venue])]
            if not batch:
                break
            selected.extend(batch)
            offset += 1
        by_date[day] = selected
    codes = []
    day_keys = sorted(by_date)
    offset = 0
    while len(codes) < limit:
        batch = [by_date[day][offset] for day in day_keys if offset < len(by_date[day])]
        if not batch:
            break
        codes.extend(batch[:limit - len(codes)])
        offset += 1
    if not codes:
        return {"status": "no_paired_archives", "formal": False, "requested": 0}
    # Diagnose the hole-mode gap using actual winning ranks, not speculative race causes.
    breakdown = {mode: {"top3": 0, "rank4_5": 0, "rank6_10": 0,
                        "rank11_plus": 0, "not_covered": 0,
                        "head_absent": 0, "second_pair_absent": 0,
                        "third_absent": 0, "ticket_count_sum": 0}
                 for mode in MODES}
    hole_pair_review = {"cases": 0, "hit_mode_has_winning_pair": 0,
                        "balance_mode_has_winning_pair": 0,
                        "hole_distinct_second_counts": {},
                        "winning_second_counts": {},
                        "missing_pair_examples": []}
    for code in codes:
        record = compare_race(code, root)
        if record.get("status") != "historical_comparison_only":
            continue
        if record["modes"]["hole"]["coverage_diagnostic"] == "winner_second_pair_absent":
            status, archive = archived_four_modes(code, root)
            if status != 200:
                raise ValueError("archived_race_changed_after_comparison")
            first, second, _ = record["winning_ticket"].split("-")
            target_pair = first + "-" + second + "-"
            hole_tickets = [entry["combo"] for entry in archive["modes"]["hole"]["tickets"]]
            actual_seconds = sorted({ticket.split("-")[1] for ticket in hole_tickets
                                     if ticket.startswith(first + "-")})
            if not actual_seconds or any(ticket.startswith(target_pair) for ticket in hole_tickets):
                raise ValueError("hole_pair_diagnostic_disagrees_with_source")
            hole_pair_review["cases"] += 1
            for mode, field in (("hit", "hit_mode_has_winning_pair"),
                                ("balance", "balance_mode_has_winning_pair")):
                if any(entry["combo"].startswith(target_pair)
                       for entry in archive["modes"][mode]["tickets"]):
                    hole_pair_review[field] += 1
            key = str(len(actual_seconds))
            hole_pair_review["hole_distinct_second_counts"][key] = (
                hole_pair_review["hole_distinct_second_counts"].get(key, 0) + 1)
            hole_pair_review["winning_second_counts"][second] = (
                hole_pair_review["winning_second_counts"].get(second, 0) + 1)
            if len(hole_pair_review["missing_pair_examples"]) < 10:
                hole_pair_review["missing_pair_examples"].append({
                    "race_code": code, "winning_pair": first + "-" + second,
                    "hole_selected_seconds_after_correct_head": actual_seconds})
        for mode in MODES:
            m = record["modes"][mode]
            rank = m["winning_rank"]
            group = ("not_covered" if rank is None else "top3" if rank <= 3 else
                     "rank4_5" if rank <= 5 else "rank6_10" if rank <= 10 else "rank11_plus")
            breakdown[mode][group] += 1
            breakdown[mode]["ticket_count_sum"] += m["ticket_count"]
            miss = {"winner_head_absent": "head_absent",
                    "winner_second_pair_absent": "second_pair_absent",
                    "winner_third_absent": "third_absent"}.get(m["coverage_diagnostic"])
            if miss:
                breakdown[mode][miss] += 1
    overall = summarize_group(codes, root, include_per_race=True)
    codes.sort()
    days = sorted(set(code[:8] for code in codes))
    venues = sorted(set(code[8:10] for code in codes))
    # A content fingerprint binds all summary metrics to an exact, auditable
    # membership roster. Dynamic archive sampling does NOT freeze that roster.
    roster_sha256 = hashlib.sha256(("\n".join(codes) + "\n").encode("ascii")).hexdigest()
    return {"status": "historical_research_only", "cohort_codes": codes,
            "cohort_sha256": roster_sha256,
            "cohort_hash_scope": "sha256_ascii_newline_join_sorted_race_codes_trailing_newline",
            "cohort_membership_frozen": False,
            **overall, "rank_and_miss_breakdown": breakdown,
            "hole_second_pair_review": hole_pair_review, "by_day": {day: summarize_group([c for c in codes if c[:8] == day], root) for day in days},
            "by_venue_code": {venue: summarize_group([c for c in codes if c[8:10] == venue], root) for venue in venues},
            "warning": "Selected earliest matching archives only. Historical coverage; not prospective proof."}

if __name__ == "__main__":
    report = run()
    output = Path("four_mode_historical_cohort_report.json")
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + chr(10), encoding="utf-8")
    print("HISTORICAL_FOUR_MODE_COHORT=" + json.dumps({
        "status": report["status"],
        "requested": report["requested"],
        "comparable": report.get("historical_comparable"),
        "cohort_sha256": report.get("cohort_sha256"),
        "cohort_membership_frozen": report.get("cohort_membership_frozen"),
        "topn": report.get("topn_hits", {}),
        "pairwise_topn": report.get("pairwise_topn", {}),
        "rank_and_miss_breakdown": report.get("rank_and_miss_breakdown", {}),
        "hole_second_pair_review": report.get("hole_second_pair_review", {}),
        "by_day": report.get("by_day", {}),
        "by_venue_code": report.get("by_venue_code", {})}, ensure_ascii=False, sort_keys=True))
