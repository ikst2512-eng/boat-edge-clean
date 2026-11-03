"""Format metadata-only GitHub step summary for T12 workflow history."""
import json
from pathlib import Path


def format_summary(data):
    if not isinstance(data, dict):
        raise ValueError("invalid inventory")
    runs = data.get("real_dispatch_runs_seen")
    artifacts = data.get("runs_with_matching_unexpired_artifacts")
    if any(type(n) is not int or n < 0 for n in (runs, artifacts)) or artifacts > runs:
        raise ValueError("invalid inventory counts")
    truncated = data.get("pagination_may_be_truncated")
    if type(truncated) is not bool:
        raise ValueError("invalid pagination status")
    return ("## Official T−12 history inventory (metadata only)\n\n"
            "| Measure | Count |\n|---|---:|\n"
            f"| Manual dispatch runs observed | {runs} |\n"
            f"| Runs with unexpired matching artifact | {artifacts} |\n"
            f"| All pages scanned | {'No' if truncated else 'Yes'} |\n\n"
            "**Verified complete T−12 pairs: not evaluated.** "
            "An artifact or a successful workflow job is not proof of source timeliness.\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory")
    parser.add_argument("summary")
    args = parser.parse_args()
    data = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    with Path(args.summary).open("a", encoding="utf-8") as target:
        target.write(format_summary(data))
