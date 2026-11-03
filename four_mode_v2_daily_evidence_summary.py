"""Read-only human summary of prospective V2 third-rate evidence.

This report is deliberately conservative: it displays paired TopN results
only when same-race capture-vs-durable-ledger reconciliation is verified.
It cannot establish pre-cutoff remote first publication or production accuracy.
"""
import argparse
import json
from pathlib import Path

TOPS = ("top3", "top5", "top10")
FIELDS = ("baseline", "candidate", "gained", "lost")
MATCHED = "bounded_frozen_roster_matched"
CAPTURE_SCHEMA = "V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1"
LEDGER_SCHEMA = "V2_THIRD_RATE_DURABLE_LEDGER_SCORE_V1"
RECONCILE_SCHEMA = "V2_THIRD_RATE_CAPTURE_LEDGER_RECONCILIATION_V1"


def _read(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if type(value) is dict else None
    except (OSError, ValueError, UnicodeError):
        return None


def _valid_daily_partition(capture):
    """Confirm every reported day is a valid partition of all paired results.

    The original nightly scorer already checks these invariants. Recheck at
    the display boundary so a truncated/edited JSON never shows partial
    improvements under a success label.
    """
    if type(capture.get("paired")) is not int or capture["paired"] <= 0:
        return False
    days = capture.get("by_race_day_jst")
    if type(days) is not dict or not days:
        return False
    overall_codes = capture.get("race_codes_paired")
    paired_scores = capture.get("paired_race_scores")
    if (type(overall_codes) is not list
            or type(paired_scores) is not list
            or len(overall_codes) != capture["paired"]
            or len(paired_scores) != capture["paired"]
            or any(type(code) is not str or len(code) != 12
                   or not code.isdecimal() or code[:8] < "20261104"
                   for code in overall_codes)
            or len(set(overall_codes)) != len(overall_codes)):
        return False
    score_codes = [row.get("race_code") for row in paired_scores
                   if type(row) is dict]
    if (len(score_codes) != capture["paired"]
            or any(type(code) is not str for code in score_codes)
            or sorted(score_codes) != sorted(overall_codes)):
        return False
    # Validate and recompute the arithmetic from individual *frozen* paired
    # race outcomes. A coherent-looking but tampered aggregate is not proof.
    by_race = {}
    for row in paired_scores:
        code = row["race_code"]
        topn = row.get("topn")
        if type(topn) is not dict or set(topn) != set(TOPS):
            return False
        for n in TOPS:
            values = topn[n]
            if (type(values) is not dict or set(values) != set(FIELDS)
                    or any(type(values[k]) is not int or
                           values[k] not in (0, 1) for k in FIELDS)
                    or values["candidate"] - values["baseline"]
                       != values["gained"] - values["lost"]
                    or (values["gained"] and values["lost"])):
                return False
        by_race[code] = topn
    paired_total = 0
    all_day_codes = []
    totals = {key: {field: 0 for field in FIELDS} for key in TOPS}
    for day, group in days.items():
        if (type(day) is not str or len(day) != 8 or not day.isdecimal()
                or day < "20261104" or type(group) is not dict
                or type(group.get("paired")) is not int or group["paired"] <= 0):
            return False
        codes = group.get("race_codes")
        if (type(codes) is not list or len(codes) != group["paired"]
                or any(type(code) is not str or code[:8] != day
                       for code in codes)
                or len(set(codes)) != len(codes)):
            return False
        all_day_codes.extend(codes)
        paired_total += group["paired"]
        topn = group.get("topn")
        if type(topn) is not dict or set(topn) != set(TOPS):
            return False
        for n in TOPS:
            values = topn[n]
            if (type(values) is not dict or set(values) != set(FIELDS)
                    or any(type(values[k]) is not int or
                           not 0 <= values[k] <= group["paired"] for k in FIELDS)
                    or values["candidate"] - values["baseline"]
                       != values["gained"] - values["lost"]):
                return False
            for field in FIELDS:
                if values[field] != sum(by_race[code][n][field] for code in codes):
                    return False
                totals[n][field] += values[field]
    if (paired_total != capture["paired"]
            or sorted(all_day_codes) != sorted(overall_codes)):
        return False
    reported = capture.get("topn")
    if (type(reported) is not dict or set(reported) != set(TOPS)
            or any(type(reported[n]) is not dict or
                   set(reported[n]) != set(FIELDS)
                   or any(type(reported[n].get(k)) is not int or
                          reported[n][k] != totals[n][k] for k in FIELDS)
                   for n in TOPS)):
        return False
    return True


def summarize(capture, ledger, reconciliation):
    capture = capture if type(capture) is dict and capture.get("schema") == CAPTURE_SCHEMA else None
    ledger = ledger if type(ledger) is dict and ledger.get("schema") == LEDGER_SCHEMA else None
    reconciliation = (reconciliation if type(reconciliation) is dict
                      and reconciliation.get("schema") == RECONCILE_SCHEMA else None)
    complete = bool(
        capture and ledger and reconciliation
        and reconciliation.get("status") == MATCHED
        and capture.get("status") == "frozen_artifacts_scored_limited_cohort"
        and capture.get("cohort_completeness_verified") is True
        and ledger.get("status") == "durable_frozen_evidence_scored"
        and not capture.get("missing_or_failed_artifacts")
        and not capture.get("bad_validation_runs")
        and not ledger.get("invalid_files")
        and _valid_daily_partition(capture))
    title = "## V2 third-rate prospective evidence (research only)"
    lines = [title, "",
             f"- Capture audit: {capture.get('status', 'unavailable') if capture else 'unavailable'}",
             f"- Durable ledger: {ledger.get('status', 'unavailable') if ledger else 'unavailable'}",
             f"- Same-race reconciliation: {reconciliation.get('status', 'unavailable') if reconciliation else 'unavailable'}",
             f"- Frozen candidates (capture): {capture.get('frozen', 'unavailable') if capture else 'unavailable'}",
             f"- Matched confirmed results (capture): {capture.get('paired', 'unavailable') if capture else 'unavailable'}",
             f"- Pending results: {capture.get('pending_results', 'unavailable') if capture else 'unavailable'}",
             f"- Frozen candidates (long-lived ledger): {ledger.get('frozen', 'unavailable') if ledger else 'unavailable'}",
             f"- Unresolved capture runs: {capture.get('pending_or_unknown_runs', 'unavailable') if capture else 'unavailable'}",
             f"- Unsuccessful capture runs: {capture.get('unsuccessful_runs', 'unavailable') if capture else 'unavailable'}",
             f"- Evidence ready for bounded research comparison: {'yes' if complete else 'no'}",
             ""]
    if not complete:
        lines.extend(["**TopN accuracy withheld:** capture, ledger, or same-race verification is incomplete.",
                      "No zero-hit assumption or accuracy claim may be made from missing evidence.", ""])
    else:
        for day, group in sorted(capture["by_race_day_jst"].items()):
            topn = group["topn"]
            lines.extend([f"### {day} / confirmed paired races: {group['paired']}",
                          "| TopN | Original hits | Candidate hits | Difference |",
                          "|---|---:|---:|---:|"])
            for n in TOPS:
                orig = topn[n]["baseline"]
                new = topn[n]["candidate"]
                lines.append(f"| {n.upper()} | {orig} | {new} | {new-orig:+d} |")
            lines.append("")
    lines.append("**Not certified:** independent GitHub remote first-seen before cutoff, untouched holdout, or production accuracy. No model promotion.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    markdown = summarize(_read(args.capture), _read(args.ledger),
                         _read(args.reconciliation))
    args.output.write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
