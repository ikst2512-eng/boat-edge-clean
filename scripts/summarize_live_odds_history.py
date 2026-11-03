"""Read-only 14-day historical trend of independently measured live odds availability.

GitHub Actions artifacts from the existing odds probe are the sole evidence.
No predictions, results, or historical result-conditioned samples are used.
"""
import io
import json
import os
import statistics
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DAYS = 14
MAX_RUNS = 100
WORKFLOW = "live-official-odds-probe.yml"
ARTIFACT = "live-odds-metrics"
FILE = "live_odds_metrics.json"



def consistent_attempts(steps):
    """Reject internally contradictory HTTP/status claims before computing rates."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= 3:
        return False
    codes = {"valid_200": 200, "invalid_200": 200, "pending_202": 202}
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or type(step.get("latency_ms")) is not int or step["latency_ms"] < 0:
            return False
        state = step.get("state")
        http = step.get("http")
        if state in codes:
            if type(http) is not int or http != codes[state]:
                return False
        elif state == "other_http":
            if type(http) is not int or http in (200, 202) or not 100 <= http <= 599:
                return False
        elif state == "http_error":
            if type(http) is not int or http in (200, 202) or not 400 <= http <= 599:
                return False
        elif isinstance(state, str) and state.startswith("transport_error:"):
            if http is not None or state == "transport_error:":
                return False
        else:
            return False
        # The live probe retries only a pending HTTP 202, never a success or failure.
        if index > 0 and steps[index - 1]["state"] != "pending_202":
            return False
    return True


def summarize(records):
    """Count observed race requests, never infer success for missing runs."""
    observations = []
    seen = set()
    eligible_runs = set()
    for run in records:
        if run.get("source_status") != "ok" or not isinstance(run.get("samples"), list):
            continue
        stamp = run.get("checked_at_jst")
        for sample in run["samples"]:
            code = sample.get("race_code") if isinstance(sample, dict) else None
            steps = sample.get("attempts") if isinstance(sample, dict) else None
            if not isinstance(code, str) or len(code) != 12 or not code.isdigit() or not isinstance(steps, list) or not steps or len(steps) > 3:
                continue
            # Same probe run + race cannot be counted twice.
            key = (stamp, code)
            if key in seen:
                continue
            if not consistent_attempts(steps):
                continue
            seen.add(key)
            eligible_runs.add(stamp)
            observations.append({"code": code, "steps": steps, "elapsed": sample.get("elapsed_ms")})
    http = Counter(str(step.get("http")) for item in observations for step in item["steps"])
    first_valid = sum(item["steps"][0]["state"] == "valid_200" for item in observations)
    pending = [item for item in observations if item["steps"][0]["state"] == "pending_202"]
    recovered = [item for item in pending if item["steps"][-1]["state"] == "valid_200"]
    valid = sum(item["steps"][-1]["state"] == "valid_200" for item in observations)
    request_times = [step["latency_ms"] for item in observations for step in item["steps"]]
    elapsed_times = [item["elapsed"] for item in observations if type(item["elapsed"]) is int and item["elapsed"] >= 0]
    return {
        "runs_with_eligible_observations": len(eligible_runs),
        "race_observations": len(observations),
        "unique_races": len({item["code"] for item in observations}),
        "requests": sum(http.values()),
        "http_200": http["200"],
        "http_202": http["202"],
        "http_503": http["503"],
        "other_http_or_transport": sum(http.values()) - http["200"] - http["202"] - http["503"],
        "first_attempt_valid_races": first_valid,
        "eventual_valid_races": valid,
        "eventual_valid_rate_pct": round(valid * 100 / len(observations), 1) if observations else None,
        "initially_pending_races": len(pending),
        "pending_recovered": len(recovered),
        "pending_recovery_rate_pct": round(len(recovered) * 100 / len(pending), 1) if pending else None,
        "median_request_latency_ms": round(statistics.median(request_times)) if request_times else None,
        "median_race_elapsed_ms": round(statistics.median(elapsed_times)) if elapsed_times else None,
    }



def daily_trends(records, *, now=None):
    """14 JST calendar days. Missing days are N/A, never zero successes."""
    jst = timezone(timedelta(hours=9))
    today = (now or datetime.now(timezone.utc)).astimezone(jst).date()
    buckets = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            stamp = datetime.fromisoformat(record["checked_at_jst"])
            if stamp.tzinfo is None:
                continue
            day = stamp.astimezone(jst).date()
        except (KeyError, TypeError, ValueError):
            continue
        if not today - timedelta(days=DAYS - 1) <= day <= today:
            continue
        buckets.setdefault(day.isoformat(), []).append(record)
    rows = []
    for offset in range(DAYS - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        records_for_day = buckets.get(day, [])
        values = summarize(records_for_day)
        rows.append({"date_jst": day, "has_valid_observations": values["race_observations"] > 0,
                     "runs_with_observations": values["runs_with_eligible_observations"],
                     "races": values["race_observations"], "http_200": values["http_200"],
                     "http_202": values["http_202"], "http_503": values["http_503"],
                     "valid_200_races": values["eventual_valid_races"],
                     "valid_rate_pct": values["eventual_valid_rate_pct"],
                     "initially_pending_races": values["initially_pending_races"],
                     "pending_recovered": values["pending_recovered"],
                     "pending_recovery_rate_pct": values["pending_recovery_rate_pct"],
                     "median_request_latency_ms": values["median_request_latency_ms"]})
    return rows


def api_json(url, token):
    with urlopen(Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "BOAT-EDGE-CLEAN-ODDS-TREND/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }), timeout=20) as response:
        return json.load(response)


def fetch_history(repository, token, current, *, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DAYS)
    root = "https://api.github.com/repos/" + repository
    runs = api_json(root + "/actions/workflows/" + WORKFLOW + "/runs?status=completed&per_page=100", token).get("workflow_runs", [])
    selected = []
    for run in runs:
        if run.get("event") not in ("schedule", "workflow_dispatch") or run.get("conclusion") != "success":
            continue
        try:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            continue
        if created < cutoff or created > now + timedelta(minutes=5):
            continue
        selected.append(run)
    history = [current]
    errors = []
    for run in selected[:MAX_RUNS]:
        run_id = run["id"]
        try:
            artifacts = api_json(root + "/actions/runs/" + str(run_id) + "/artifacts?per_page=100", token).get("artifacts", [])
            item = next((x for x in artifacts if x.get("name") == ARTIFACT and not x.get("expired")), None)
            if not item:
                errors.append({"run_id": run_id, "status": "missing_artifact"})
                continue
            req = Request(root + "/actions/artifacts/" + str(item["id"]) + "/zip", headers={
                "Authorization": "Bearer " + token, "User-Agent": "BOAT-EDGE-CLEAN-ODDS-TREND/1.0"})
            with urlopen(req, timeout=25) as response:
                raw = response.read(2_000_000)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if FILE not in archive.namelist():
                    raise ValueError("METRICS_JSON_MISSING")
                if archive.getinfo(FILE).file_size > 200_000:
                    raise ValueError("METRICS_JSON_TOO_LARGE")
                evidence = json.loads(archive.read(FILE))
            if not isinstance(evidence, dict) or not isinstance(evidence.get("samples"), list):
                raise ValueError("METRICS_SCHEMA")
            # Only evidence with the source's actual observation timestamp.
            stamp = datetime.fromisoformat(evidence["checked_at_jst"])
            if stamp.tzinfo is None or stamp.astimezone(timezone.utc) < cutoff:
                raise ValueError("METRICS_TIME_INVALID")
            history.append(evidence)
        except (HTTPError, URLError, OSError, ValueError, KeyError, zipfile.BadZipFile, TimeoutError) as exc:
            errors.append({"run_id": run_id, "status": type(exc).__name__})
    return history, len(selected), errors


def main():
    current_file = Path(FILE)
    if not current_file.is_file():
        raise SystemExit("CURRENT_METRICS_MISSING")
    current = json.loads(current_file.read_text(encoding="utf-8"))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    history = [current]
    scanned = 0
    errors = []
    status = "ok"
    if not token or "/" not in repo:
        status = "history_access_not_configured"
    else:
        try:
            history, scanned, errors = fetch_history(repo, token, current)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            status = "history_api_unavailable:" + type(exc).__name__
    if status == "ok" and errors:
        status = "partial_history"
    metrics = summarize(history)
    daily = daily_trends(history)
    report = {"window_days": DAYS, "status": status, "history_runs_selected": scanned,
              "history_evidence_loaded": len(history) - 1, "history_errors": errors,
              "includes_current_run": True, "metrics": metrics, "daily": daily}
    Path("live_odds_14day_trend.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("LIVE_ODDS_14DAY_TREND " + json.dumps(report, ensure_ascii=False), flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("\n### 14-day live odds trend (observations, not formal accuracy)\n\n")
            stream.write("Historical artifact availability: " + status + "; historical runs loaded: " +
                         str(len(history) - 1) + "/" + str(scanned) + "; errors: " + str(len(errors)) + "\n\n")
            stream.write("Race observations: " + str(metrics["race_observations"]) +
                         "; eventual valid rate: " + str(metrics["eventual_valid_rate_pct"]) +
                         "%; first-attempt valid: " + str(metrics["first_attempt_valid_races"]) + "\n\n")
            stream.write("HTTP 202 requests: " + str(metrics["http_202"]) +
                         "; 202 recovery: " + str(metrics["pending_recovered"]) + "/" +
                         str(metrics["initially_pending_races"]) + " (" +
                         str(metrics["pending_recovery_rate_pct"]) + "%)\n\n")
            stream.write("Median request latency: " + str(metrics["median_request_latency_ms"]) + "ms\n\n")
            stream.write("Observed JST dates: " + str(sum(row["has_valid_observations"] for row in daily)) +
                         "/14; missing days are N/A, not successes.\n\n")
            stream.write("Missing runs and unavailable history are not counted as successes.\n")


if __name__ == "__main__":
    main()
