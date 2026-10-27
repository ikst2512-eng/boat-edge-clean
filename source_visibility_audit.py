"""Read-only diagnostics for the legacy public data consumed by CLEAN.

No formal prediction generation, scoring, source migration or writes.
Exit nonzero when today's manifest cannot be read; missing race feeds are
reported separately because absent pre-race predictions can be legitimate.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://raw.githubusercontent.com/ikst2512-eng/boat-edge/main/data/"
JST = timezone(timedelta(hours=9))


def get_json(path):
    try:
        req = Request(BASE + path, headers={"User-Agent": "boat-edge-clean-source-audit/1.0"})
        with urlopen(req, timeout=12) as response:
            if response.status != 200:
                return None, f"HTTP_{response.status}"
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                return None, "OVERSIZE"
            return json.loads(payload), None
    except HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def audit(day=None):
    day = day or datetime.now(JST).strftime("%Y-%m-%d")
    manifest, err = get_json("today.json")
    report = {"requested_date": day, "manifest_error": err,
              "manifest_date": None, "manifest_updated_at": None,
              "races": 0, "prediction_present": 0, "prediction_missing": 0,
              "result_present": 0, "result_missing": 0, "other_errors": [],
              "reference_prediction_present": 0, "confirmed_result_present": 0,
              "prediction_missing_keys": [], "result_missing_keys": []}
    if not isinstance(manifest, dict):
        report["manifest_error"] = err or "INVALID_MANIFEST"
        return report
    report["manifest_date"] = manifest.get("date")
    report["manifest_updated_at"] = manifest.get("updated_at")
    if report["manifest_date"] != day:
        report["manifest_error"] = "STALE_MANIFEST_DATE"
        return report
    venues = manifest.get("venues")
    if not isinstance(venues, list):
        report["manifest_error"] = "INVALID_VENUES"
        return report
    # Check a deterministic sample to keep API load modest. Counts are sample,
    # not whole-day availability. Do not confuse 404 with an operational failure.
    for venue in venues[:3]:
        if not isinstance(venue, dict):
            continue
        jcd = str(venue.get("jcd", "")).zfill(2)
        races = venue.get("races")
        if len(jcd) != 2 or not jcd.isdigit() or not isinstance(races, list):
            continue
        for race in races[:2]:
            if not isinstance(race, dict):
                continue
            try:
                number = int(race["race_no"])
                if not 1 <= number <= 12:
                    continue
            except (KeyError, ValueError, TypeError):
                continue
            key = f"{day.replace('-', '')}-{jcd}-{number:02d}"
            report["races"] += 1
            for category, prefix in (("prediction", "site_prediction_snapshots"),
                                     ("result", "site_results")):
                obj, error = get_json(f"{prefix}/{key}.json")
                if error == "HTTP_404":
                    report[category + "_missing"] += 1
                    report[category + "_missing_keys"].append(key)
                elif error is not None or not isinstance(obj, dict):
                    report["other_errors"].append({"feed": category, "key": key, "error": error or "INVALID_JSON"})
                else:
                    report[category + "_present"] += 1
                    if category == "prediction" and obj.get("prediction_kind") == "SITE_REFERENCE_V122":
                        report["reference_prediction_present"] += 1
                    if category == "result" and obj.get("status") == "confirmed":
                        report["confirmed_result_present"] += 1
    return report


if __name__ == "__main__":
    report = audit(os.environ.get("AUDIT_DATE") or None)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as out:
        out.write("## CLEAN upstream visibility (read-only)\n")
        out.write(f"- Day: {report['requested_date']} / manifest: {report['manifest_date']} / updated: {report['manifest_updated_at']}\n")
        out.write(f"- Sampled races: {report['races']} (up to six; not whole-day coverage)\n")
        out.write(f"- Formal prediction files: present={report['prediction_present']}, 404={report['prediction_missing']}\n")
        out.write(f"- Result files: present={report['result_present']}, 404={report['result_missing']}\n")
        out.write(f"- Manifest issue: {report['manifest_error']}; other errors: {json.dumps(report['other_errors'], ensure_ascii=False)}\n")
        out.write(f"- Site-reference snapshots (NOT formal-verified): {report['reference_prediction_present']} / {report['prediction_present']} present\n")
        out.write(f"- Confirmed results: {report['confirmed_result_present']} / {report['result_present']} present\n")
        out.write(f"- Missing sample race keys: prediction={report['prediction_missing_keys']}, result={report['result_missing_keys']}\n")
        out.write("- Presence does not prove first-Git-add validation or official Fresh publication.\n")
        out.write("- Missing files are NOT proof of a failed collector or permission to backfill after cutoff.\n")
    if report["manifest_error"] or report["other_errors"]:
        raise SystemExit(1)
