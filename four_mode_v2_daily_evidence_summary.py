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
        and not ledger.get("invalid_files"))
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
        daily = capture.get("by_race_day_jst")
        if type(daily) is not dict:
            lines.extend(["**TopN accuracy withheld:** daily score partition is missing.", ""])
        else:
            displayed = 0
            for day in sorted(daily):
                if day < "20261104":
                    continue
                group = daily[day]
                if type(group) is not dict or type(group.get("paired")) is not int:
                    continue
                topn = group.get("topn")
                if type(topn) is not dict or any(
                        type(topn.get(n)) is not dict or
                        any(type(topn[n].get(field)) is not int for field in FIELDS)
                        for n in TOPS):
                    continue
                displayed += 1
                lines.extend([f"### {day} / confirmed paired races: {group['paired']}",
                              "| TopN | Original hits | Candidate hits | Difference |",
                              "|---|---:|---:|---:|"])
                for n in TOPS:
                    orig = topn[n]["baseline"]
                    new = topn[n]["candidate"]
                    lines.append(f"| {n.upper()} | {orig} | {new} | {new-orig:+d} |")
                lines.append("")
            if displayed == 0:
                lines.extend(["No future-day confirmed pairs available for comparison.", ""])
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
