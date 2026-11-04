"""Optional post-verdict forensic capture of failed public official odds HTML.

This step must run only AFTER the operational metrics and strict verdict.
A later HTML GET is not the upstream bytes observed by Render and cannot
turn a failed race into a successful 120-ticket operational sample.
"""
import json
from pathlib import Path

from probe_live_odds_health import preserve_failed_official_html


def main():
    path = Path("live_odds_metrics.json")
    if not path.is_file():
        print("LIVE_ODDS_FORENSIC_DIAGNOSTIC missing_operational_metrics", flush=True)
        return
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        samples = record.get("samples")
        if not isinstance(samples, list):
            raise ValueError("invalid_samples")
        reports = preserve_failed_official_html(samples)
        print("LIVE_ODDS_FORENSIC_DIAGNOSTIC " + json.dumps({
            "diagnostic_only": True,
            "followups": len(reports),
            "captured": sum(x.get("result") == "captured_followup_html" for x in reports),
            "unavailable": sum(x.get("result") != "captured_followup_html" for x in reports),
        }), flush=True)
    except (OSError, ValueError, TypeError) as exc:
        # The primary odds verdict is already frozen; a failed diagnostic
        # must never change its operational meaning.
        print("LIVE_ODDS_FORENSIC_DIAGNOSTIC " + json.dumps({
            "diagnostic_only": True, "error_class": type(exc).__name__,
            "result": "followup_unavailable",
        }), flush=True)


if __name__ == "__main__":
    main()
