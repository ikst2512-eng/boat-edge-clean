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
MAX_RUNS = 250
MAX_PAGES = 12
WORKFLOW = "live-official-odds-probe.yml"
ARTIFACT = "live-odds-metrics"
FILE = "live_odds_metrics.json"



def consistent_attempts(steps):
    """Reject internally contradictory HTTP/status claims before computing rates."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= 3:
        return False
    codes = {"valid_200": 200, "invalid_200": 200, "pending_202": 202}
    # Historical artifacts predate the per-attempt UTC fields. Preserve those
    # records, but never accept a partially timestamped or contradictory new
    # sequence as precise evidence of when HTTP odds were observed.
    timestamped = any(
        isinstance(step, dict) and
        ("started_at_utc" in step or "finished_at_utc" in step)
        for step in steps)
    previous_finish = None
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or type(step.get("latency_ms")) is not int or step["latency_ms"] < 0:
            return False
        if timestamped:
            try:
                started = datetime.fromisoformat(step["started_at_utc"].replace("Z", "+00:00"))
                finished = datetime.fromisoformat(step["finished_at_utc"].replace("Z", "+00:00"))
                if (started.utcoffset() != timedelta(0)
                        or finished.utcoffset() != timedelta(0)
                        or started > finished
                        or (previous_finish is not None and started < previous_finish)):
                    return False
                previous_finish = finished
            except (KeyError, AttributeError, TypeError, ValueError):
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
        # Mirror the live probe: pending 202 permits another request up to
        # three attempts; only an initial TimeoutError gets one retry.
        if index > 0:
            prior = steps[index - 1]["state"]
            if prior != "pending_202" and not (
                    index == 1 and prior == "transport_error:TimeoutError"):
                return False
    return True



def consistent_observation_times(steps, checked_at_jst):
    """Ensure new UTC attempts belong to the run's actual observation period.

    Legacy attempts without timestamps keep their pre-existing classification,
    but cannot establish exact HTTP timing.
    """
    if not consistent_attempts(steps):
        return False
    if not any("started_at_utc" in step for step in steps):
        return True
    try:
        checked = datetime.fromisoformat(checked_at_jst).astimezone(timezone.utc)
        if datetime.fromisoformat(checked_at_jst).tzinfo is None:
            return False
        first = datetime.fromisoformat(steps[0]["started_at_utc"].replace("Z", "+00:00"))
        last = datetime.fromisoformat(steps[-1]["finished_at_utc"].replace("Z", "+00:00"))
    except (TypeError, AttributeError, ValueError, KeyError):
        return False
    # Source discovery runs before HTTP sampling. A valid attempt cannot
    # precede this run, or be attributed to a different run hours later.
    return (checked - timedelta(minutes=1) <= first <= checked + timedelta(hours=1)
            and last <= checked + timedelta(hours=1))


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
            if not consistent_observation_times(steps, stamp):
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



def schedule_trigger_health(runs, *, now=None, grace_minutes=90, day=None, earliest_possible=None,
                            schedule_configured_at=None):
    """Observe today's configured cron slots; missing triggers are not API failures.

    A late GitHub scheduled event may arrive after this check, so "not_observed"
    is an audit warning rather than proof of scheduler failure.
    """
    utc_now = now or datetime.now(timezone.utc)
    jst = timezone(timedelta(hours=9))
    day = day or utc_now.astimezone(jst).date()
    slots = []
    for hour in (3, 5, 7):  # 12:25, 14:25, 16:25 JST, as configured in workflow
        scheduled = datetime.combine(day, datetime.min.time(), tzinfo=jst).replace(
            hour=hour + 9, minute=25).astimezone(timezone.utc)
        deadline = scheduled + timedelta(minutes=grace_minutes)
        observed = []
        for run in runs:
            if not isinstance(run, dict) or run.get("event") != "schedule":
                continue
            try:
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                if created.tzinfo is not None and scheduled <= created <= deadline:
                    observed.append({"run_id": run.get("id"), "status": run.get("status"),
                                     "conclusion": run.get("conclusion"),
                                     "created_at": run["created_at"]})
            except (KeyError, TypeError, ValueError):
                continue
        # GitHub could not have triggered the workflow before this repository existed.
        # Creation time is a lower bound only, not proof the cron was enabled then.
        if earliest_possible is not None and scheduled < earliest_possible:
            state = "before_repository_creation"
        elif schedule_configured_at is not None and scheduled < schedule_configured_at:
            state = "before_schedule_enabled"
        else:
            state = "observed" if observed else ("not_observed_after_grace" if utc_now >= deadline else "awaiting_grace")
        slots.append({"scheduled_jst": scheduled.astimezone(jst).isoformat(),
                      "state": state, "matching_runs": observed})
    # Do not attribute an hours-late schedule event to a particular cron
    # slot: the shared cron expression does not encode its intended hour.
    # Preserve such runs separately from the on-time slot coverage numerator.
    windows = [
        (datetime.fromisoformat(item["scheduled_jst"]).astimezone(timezone.utc),
         datetime.fromisoformat(item["scheduled_jst"]).astimezone(timezone.utc)
         + timedelta(minutes=grace_minutes))
        for item in slots
    ]
    unattributed = []
    for run in runs:
        if not isinstance(run, dict) or run.get("event") != "schedule":
            continue
        try:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError):
            continue
        if (created.tzinfo is None or created.astimezone(jst).date() != day
                or created < windows[0][0] or created > utc_now):
            continue
        if any(start <= created <= end for start, end in windows):
            continue
        unattributed.append({"run_id": run.get("id"), "created_at": run["created_at"],
                             "conclusion": run.get("conclusion"),
                             "status": run.get("status")})
    return {"observed_slots": sum(s["state"] == "observed" for s in slots),
            "not_observed_after_grace": sum(s["state"] == "not_observed_after_grace" for s in slots),
            "grace_minutes": grace_minutes, "slots": slots,
            "outside_grace_unattributed_runs": unattributed}


def schedule_history_coverage(runs, *, now=None, days=DAYS, grace_minutes=90,
                              earliest_possible=None, schedule_configured_at=None):
    """Track observed schedule events over calendar days, not API success.

    Missing scheduled trigger observations are not evidence that GitHub attempted
    and failed the API probe; they are separate operational coverage gaps.
    """
    now = now or datetime.now(timezone.utc)
    jst = timezone(timedelta(hours=9))
    today = now.astimezone(jst).date()
    daily = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        slot_status = schedule_trigger_health(runs, now=now, day=day,
                                              grace_minutes=grace_minutes,
                                              earliest_possible=earliest_possible,
                                              schedule_configured_at=schedule_configured_at)
        daily.append({"date_jst": day.isoformat(), **slot_status})
    total = sum(len(row["slots"]) for row in daily)
    observed = sum(row["observed_slots"] for row in daily)
    missing = sum(row["not_observed_after_grace"] for row in daily)
    ineligible = sum(sum(slot["state"] == "before_repository_creation" for slot in row["slots"])
                     for row in daily)
    before_enabled = sum(sum(slot["state"] == "before_schedule_enabled" for slot in row["slots"])
                         for row in daily)
    return {"calendar_days": days, "slots_configured": total,
            "slots_before_repository_creation": ineligible,
            "slots_before_schedule_enabled": before_enabled,
            "eligible_slots": total - ineligible - before_enabled,
            "observed_slots": observed, "not_observed_after_grace": missing,
            "awaiting_grace": total - observed - missing - ineligible - before_enabled,
            "observed_rate_pct": round(100 * observed / (observed + missing), 1)
            if observed + missing else None,
            "daily": daily}


def fetch_schedule_trigger_health(repository, token, *, now=None):
    root = "https://api.github.com/repos/" + repository
    url = root + "/actions/workflows/" + WORKFLOW + "/runs?event=schedule&per_page=100"
    payload = api_json(url, token)
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        raise ValueError("SCHEDULE_RUN_LIST_INVALID")
    metadata = api_json(root, token)
    try:
        created_at = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            raise ValueError("REPOSITORY_CREATED_AT_NAIVE")
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError("REPOSITORY_CREATED_AT_INVALID") from exc
    # The odds workflow did not exist before its initial scheduled-workflow
    # commit (c111da08a0a1). Repository creation predates this monitor.
    scheduled_since = datetime.fromisoformat("2026-10-31T06:38:46+00:00")
    return {**schedule_trigger_health(runs, now=now, earliest_possible=created_at,
                                      schedule_configured_at=scheduled_since),
            "history_14day": schedule_history_coverage(
                runs, now=now, earliest_possible=created_at,
                schedule_configured_at=scheduled_since),
            "repository_created_at": created_at.isoformat(),
            "schedule_configured_at": scheduled_since.isoformat()}



def api_json(url, token):
    with urlopen(Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "BOAT-EDGE-CLEAN-ODDS-TREND/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }), timeout=20) as response:
        return json.load(response)


def plausible_fallback_run_time(created):
    """Prefilter completed fallback runs, never PR smoke or unrelated upstream hours.

    A verified source can start as early as 12:35/14:35/16:35 JST.
    GitHub may delay the corresponding workflow_run by up to 60 minutes, so
    allow a deliberately broad window before verifying its artifact.
    """
    jst = timezone(timedelta(hours=9))
    local = created.astimezone(jst)
    minute_of_day = local.hour * 60 + local.minute
    return any(hour * 60 + 35 <= minute_of_day <= (hour + 1) * 60 + 55
               for hour in (12, 14, 16))


def fetch_history(repository, token, current, *, now=None):
    now = now or datetime.now(timezone.utc)
    # Match the 14 calendar days displayed by daily_trends(), not a rolling 336h.
    jst = timezone(timedelta(hours=9))
    first_day = now.astimezone(jst).date() - timedelta(days=DAYS - 1)
    cutoff = datetime.combine(first_day, datetime.min.time(), tzinfo=jst).astimezone(timezone.utc)
    root = "https://api.github.com/repos/" + repository
    # Event-specific queries prevent large PR and upstream fallback traffic
    # from pushing the 14-day scheduled evidence outside the first N pages.
    selected = []
    list_truncated = False
    # Manual workflow_dispatch is QA, never unattended reliability evidence.
    for event in ("schedule", "workflow_run"):
        for page in range(1, MAX_PAGES + 1):
            payload = api_json(root + "/actions/workflows/" + WORKFLOW +
                               "/runs?status=completed&event=" + event +
                               "&per_page=100&page=" + str(page), token)
            batch = payload.get("workflow_runs") if isinstance(payload, dict) else None
            if not isinstance(batch, list):
                raise ValueError("WORKFLOW_RUN_LIST_INVALID")
            past_cutoff = False
            for run in batch:
                if not isinstance(run, dict) or run.get("event") != event:
                    continue
                try:
                    created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                if created.tzinfo is None:
                    continue
                if created < cutoff:
                    past_cutoff = True
                    continue
                if created > now + timedelta(minutes=5):
                    continue
                if event == "workflow_run" and not plausible_fallback_run_time(created):
                    continue
                selected.append(run)
            if len(batch) < 100 or past_cutoff:
                break
            if page == MAX_PAGES:
                list_truncated = True
    selected.sort(key=lambda r: r["created_at"], reverse=True)
    history = [current]
    errors = []
    if list_truncated:
        errors.append({"run_id": None, "status": "workflow_run_list_truncated"})
    if len(selected) > MAX_RUNS:
        errors.append({"run_id": None, "status": "history_run_limit_exceeded"})
    for run in selected[:MAX_RUNS]:
        run_id = run["id"]
        if run.get("conclusion") != "success":
            errors.append({"run_id": run_id, "status": "workflow_" + str(run.get("conclusion") or "unknown")})
            continue
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
            if run.get("event") == "workflow_run" and evidence.get("source_status") == "fallback_ineligible":
                # Deliberately skipped upstream PR/push/manual events are neither
                # operational successes nor missing evidence.
                continue
            if run.get("event") == "workflow_run" and not include_current_event("workflow_run", evidence):
                raise ValueError("FALLBACK_PROVENANCE_INVALID")
            # Only evidence with the source's actual observation timestamp.
            stamp = datetime.fromisoformat(evidence["checked_at_jst"])
            observed = stamp.astimezone(timezone.utc) if stamp.tzinfo is not None else None
            created_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if (observed is None or observed < cutoff or observed > now + timedelta(minutes=5)
                    or abs((observed - created_at).total_seconds()) > 3600):
                raise ValueError("METRICS_TIME_INVALID")
            history.append(evidence)
        except (HTTPError, URLError, OSError, ValueError, KeyError, zipfile.BadZipFile, TimeoutError) as exc:
            errors.append({"run_id": run_id, "status": type(exc).__name__})
    return history, len(selected), errors


def include_current_event(event, evidence=None):
    """Only independently verifiable operational events enter reliability rates."""
    if event == "schedule":
        return True
    if event != "workflow_run" or not isinstance(evidence, dict):
        return False
    trigger = evidence.get("trigger")
    return (isinstance(trigger, dict)
            and trigger.get("event") == "workflow_run"
            and trigger.get("upstream_event") == "schedule"
            and trigger.get("upstream_workflow") in ("CLEAN prospective pre-cutoff capture",
                                                     "Four-mode prospective capture (research only)")
            and trigger.get("upstream_branch") == "main"
            and type(trigger.get("upstream_run_id")) is int
            and trigger["upstream_run_id"] > 0)


def main():
    current_file = Path(FILE)
    if not current_file.is_file():
        raise SystemExit("CURRENT_METRICS_MISSING")
    current = json.loads(current_file.read_text(encoding="utf-8"))
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    include_current = include_current_event(event, current)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    history = [current] if include_current else []
    scanned = 0
    errors = []
    status = "ok"
    if not token or "/" not in repo:
        status = "history_access_not_configured"
    else:
        try:
            history, scanned, errors = fetch_history(repo, token, current)
            if not include_current:
                history = history[1:]
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            status = "history_api_unavailable:" + type(exc).__name__
    if status == "ok" and errors:
        status = "partial_history"
    if status == "ok" and not history:
        status = "no_eligible_monitoring_evidence"
    schedule_health = {"status": "not_checked"}
    if token and "/" in repo:
        try:
            schedule_health = {"status": "ok", **fetch_schedule_trigger_health(repo, token)}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            schedule_health = {"status": "unavailable:" + type(exc).__name__}
    metrics = summarize(history)
    daily = daily_trends(history)
    event_counts = {}
    for item in history:
        trigger = item.get("trigger") if isinstance(item, dict) else None
        source_event = trigger.get("event") if isinstance(trigger, dict) else "legacy"
        event_counts[source_event] = event_counts.get(source_event, 0) + 1
    report = {"window_days": DAYS, "status": status, "history_runs_selected": scanned,
              "history_evidence_loaded": max(0, len(history) - (1 if include_current else 0)),
              "history_errors": errors, "includes_current_run": include_current,
              "source_event": event or "unknown", "operational_evidence_events": event_counts,
              "metrics": metrics, "daily": daily,
              "schedule_trigger_health": schedule_health}
    Path("live_odds_14day_trend.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("LIVE_ODDS_14DAY_TREND " + json.dumps(report, ensure_ascii=False), flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("\n### 14-day live odds trend (observations, not formal accuracy)\n\n")
            stream.write("Historical artifact availability: " + status + "; historical runs loaded: " +
                         str(max(0, len(history) - (1 if include_current else 0))) + "/" + str(scanned) +
                         "; errors: " + str(len(errors)) + "\n\n")
            stream.write("Current run: " + (event or "unknown") +
                         "; included in monitoring rates: " + str(include_current) +
                         ". PR API checks are QA only.\n\n")
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
            stream.write("Today's scheduled trigger observations: " +
                         json.dumps(schedule_health, ensure_ascii=False) + "\n\n")
            if schedule_health.get("history_14day"):
                h = schedule_health["history_14day"]
                stream.write("14-day cron slot coverage: observed " + str(h["observed_slots"]) +
                             "/" + str(h["eligible_slots"]) + " eligible slots; " +
                             str(h["slots_before_repository_creation"]) + " slots predate repository; " +
                str(h["slots_before_schedule_enabled"]) + " slots predate the actual workflow schedule; not observed after grace: " +
                             str(h["not_observed_after_grace"]) + "; awaiting grace: " +
                             str(h["awaiting_grace"]) + ". This measures trigger evidence, not API success.\\n\\n")
            stream.write("Unobserved scheduled triggers are not counted as successful checks.\n")


if __name__ == "__main__":
    main()
