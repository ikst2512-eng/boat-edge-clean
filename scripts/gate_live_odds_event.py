"""Fail-closed gate for alternate odds probe triggers.

The existing CLEAN prospective workflow sometimes receives real schedule events
when the odds cron has no observed schedule trigger. Only such completed
scheduled upstream runs are eligible for fallback operational sampling.
"""
import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from probe_live_odds_health import event_provenance
from check_live_odds_probe_verdict import verdict

UPSTREAM = "CLEAN prospective pre-cutoff capture"
SECONDARY_UPSTREAM = "Four-mode prospective capture (research only)"


def fallback_slot_eligible(trigger, *, now=None):
    """Allow only the upstream 12:45/14:45/16:45 JST catch-up windows.

    The upstream is scheduled each 15 minutes; counting every completion would
    flood operational evidence and inflate the success denominator. Fail closed
    on missing, stale, future, or out-of-window timestamps.
    """
    try:
        source = datetime.fromisoformat(trigger["upstream_created_at"].replace("Z", "+00:00"))
        if source.tzinfo is None:
            return False
        source = source.astimezone(timezone.utc)
    except (KeyError, AttributeError, TypeError, ValueError):
        return False
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 <= (now - source).total_seconds() <= 60 * 60:
        return False
    jst = timezone(timedelta(hours=9))
    source_local = source.astimezone(jst)
    minimum_delay = 10 if trigger.get('upstream_workflow') == SECONDARY_UPSTREAM else 15
    for hour in (12, 14, 16):
        cutoff = source_local.replace(hour=hour, minute=25, second=0, microsecond=0)
        elapsed_minutes = (source_local - cutoff).total_seconds() / 60
        if minimum_delay <= elapsed_minutes < 30:
            return True
    return False


def eligible(event, trigger, *, now=None):
    if event in ("schedule", "workflow_dispatch", "pull_request"):
        return True  # PRs are separately excluded by the reliability aggregator.
    if event != "workflow_run" or not isinstance(trigger, dict):
        return False
    return (trigger.get("event") == "workflow_run"
            and trigger.get("upstream_event") == "schedule"
            and trigger.get("upstream_workflow") in (UPSTREAM, SECONDARY_UPSTREAM)
            and trigger.get("upstream_branch") == "main"
            and type(trigger.get("upstream_run_id")) is int
            and trigger["upstream_run_id"] > 0
            and fallback_slot_eligible(trigger, now=now))




def direct_probe_evidence(repository, token, run_id, *, fetch_json=None, fetch_zip=None,
                          expected_slot=None, run_created_at=None):
    """Only a validated saved 200 counts as completed direct monitoring.

    Returns valid, no_valid_odds, or unavailable. Metadata/ZIP network errors
    are unknown (fail closed); a successful run with no artifact is not valid.
    """
    root = "https://api.github.com/repos/" + repository
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BOAT-EDGE-CLEAN-ODDS-FALLBACK-GUARD/1.0",
    }
    try:
        url = root + "/actions/runs/" + str(run_id) + "/artifacts?per_page=100"
        if fetch_json is None:
            with urlopen(Request(url, headers=headers), timeout=15) as response:
                payload = json.load(response)
        else:
            payload = fetch_json(url, token)
        artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
        if not isinstance(artifacts, list):
            return "unavailable"
        artifact = next((x for x in artifacts if isinstance(x, dict)
                         and x.get("name") == "live-odds-metrics" and not x.get("expired")), None)
        if artifact is None:
            return "no_valid_odds"
        artifact_id = artifact.get("id")
        if type(artifact_id) is not int or artifact_id <= 0:
            return "unavailable"
        archive_url = root + "/actions/artifacts/" + str(artifact_id) + "/zip"
        if fetch_zip is None:
            with urlopen(Request(archive_url, headers=headers), timeout=20) as response:
                raw = response.read(2_000_001)
        else:
            raw = fetch_zip(archive_url, token)
        if not isinstance(raw, bytes) or len(raw) > 2_000_000:
            return "unavailable"
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if "live_odds_metrics.json" not in archive.namelist():
                return "no_valid_odds"
            if archive.getinfo("live_odds_metrics.json").file_size > 200_000:
                return "unavailable"
            data = json.loads(archive.read("live_odds_metrics.json"))
        if not isinstance(data, dict) or data.get("source_status") != "ok":
            return "no_valid_odds"
        if expected_slot is not None:
            provenance = data.get("trigger")
            if not isinstance(provenance, dict) or run_created_at is None:
                return "no_valid_odds"
            # The archived odds result must belong to an admitted scheduled
            # upstream for this same slot, not a manual/PR/skipped run.
            if not eligible("workflow_run", provenance, now=run_created_at):
                return "no_valid_odds"
            try:
                created = datetime.fromisoformat(
                    provenance["upstream_created_at"].replace("Z", "+00:00"))
                local = created.astimezone(timezone(timedelta(hours=9)))
                slot_local = min(
                    (local.replace(hour=h, minute=25, second=0, microsecond=0)
                     for h in (12, 14, 16)),
                    key=lambda candidate: abs((local - candidate).total_seconds()))
                if slot_local.astimezone(timezone.utc) != expected_slot:
                    return "no_valid_odds"
            except (KeyError, TypeError, ValueError, AttributeError):
                return "no_valid_odds"
        # Share the exact operational verdict with the unattended job.
        # In particular, legacy receipts without UTC HTTP timestamps must
        # never suppress another valid scheduled-slot fallback attempt.
        return "valid" if verdict(data) == "valid_200_observed" else "no_valid_odds"
    except (OSError, TimeoutError, ValueError, TypeError, KeyError,
            HTTPError, URLError, zipfile.BadZipFile, json.JSONDecodeError):
        return "unavailable"


def direct_schedule_guard(trigger, repository, token, *, now=None, fetch_json=None, probe_check=None):
    """Fail closed if normal cron ran or its state cannot be verified.

    Only an absent/failed scheduled probe permits the upstream fallback.
    The upstream's JST day and the three fixed slot times define the window.
    """
    if not repository or "/" not in repository or not token:
        return "schedule_lookup_unavailable"
    try:
        source = datetime.fromisoformat(trigger["upstream_created_at"].replace("Z", "+00:00"))
        if source.tzinfo is None:
            return "schedule_lookup_unavailable"
        jst = timezone(timedelta(hours=9))
        local = source.astimezone(jst)
        hour = min((12, 14, 16), key=lambda h: abs((local - local.replace(hour=h, minute=25, second=0, microsecond=0)).total_seconds()))
        slot = local.replace(hour=hour, minute=25, second=0, microsecond=0).astimezone(timezone.utc)
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        url = ("https://api.github.com/repos/" + repository +
               "/actions/workflows/live-official-odds-probe.yml/runs?event=schedule&per_page=100")
        if fetch_json is None:
            request = Request(url, headers={
                "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "BOAT-EDGE-CLEAN-ODDS-FALLBACK-GUARD/1.0"})
            with urlopen(request, timeout=15) as response:
                payload = json.load(response)
        else:
            payload = fetch_json(url, token)
        runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
        if not isinstance(runs, list):
            return "schedule_lookup_unavailable"
        for run in runs:
            if not isinstance(run, dict) or run.get("event") != "schedule":
                continue
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created.tzinfo is None:
                return "schedule_lookup_unavailable"
            if not slot <= created <= now:
                continue
            if run.get("status") != "completed":
                return "direct_schedule_observed"
            if run.get("conclusion") == "success":
                run_id = run.get("id")
                if type(run_id) is not int or run_id <= 0:
                    return "schedule_lookup_unavailable"
                state = ((probe_check or direct_probe_evidence)(repository, token, run_id))
                if state == "valid":
                    return "direct_schedule_observed"
                if state != "no_valid_odds":
                    return "schedule_lookup_unavailable"
        return "direct_schedule_absent_or_failed"
    except (KeyError, TypeError, ValueError, OSError, TimeoutError, HTTPError, URLError):
        return "schedule_lookup_unavailable"



def prior_fallback_guard(trigger, repository, token, current_run_id, *, now=None, fetch_json=None, probe_check=None):
    """Avoid two valid fallback samples for the same cron slot.

    Unknown workflow API or artifact evidence fails closed, never silently
    counts a prior green workflow as a valid odds sample.
    """
    if not repository or "/" not in repository or not token or not current_run_id:
        print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": "configuration", "reason": "missing_required_input"}), flush=True)
        return "fallback_lookup_unavailable"
    stage = "parse_upstream"
    page_seen = 0
    runs_examined = 0
    try:
        source = datetime.fromisoformat(trigger["upstream_created_at"].replace("Z", "+00:00"))
        if source.tzinfo is None:
            print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "reason": "naive_timestamp"}), flush=True)
            return "fallback_lookup_unavailable"
        jst = timezone(timedelta(hours=9))
        local = source.astimezone(jst)
        hour = min((12, 14, 16), key=lambda h: abs((local - local.replace(
            hour=h, minute=25, second=0, microsecond=0)).total_seconds()))
        slot = local.replace(hour=hour, minute=25, second=0, microsecond=0).astimezone(timezone.utc)
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        url = ("https://api.github.com/repos/" + repository +
               "/actions/workflows/live-official-odds-probe.yml/runs?event=workflow_run&per_page=100")
        # A busy repository can produce more than 100 upstream PR events in
        # one slot. Search further pages or fail closed; never assume absence.
        for page in range(1, 6):
            stage = "history_page"
            page_seen = page
            page_url = url + "&page=" + str(page)
            if fetch_json is None:
                request = Request(page_url, headers={
                    "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "BOAT-EDGE-CLEAN-ODDS-FALLBACK-GUARD/1.0"})
                with urlopen(request, timeout=15) as response:
                    payload = json.load(response)
            else:
                payload = fetch_json(page_url, token)
            runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
            if not isinstance(runs, list):
                print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "page": page_seen, "runs_examined": runs_examined, "reason": "malformed_history_response"}), flush=True)
                return "fallback_lookup_unavailable"
            older_than_slot = False
            for run in runs:
                runs_examined += 1
                if not isinstance(run, dict) or run.get("event") != "workflow_run":
                    continue
                if run.get("id") == current_run_id:
                    continue
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                if created.tzinfo is None:
                    print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "page": page_seen, "runs_examined": runs_examined, "reason": "naive_run_timestamp"}), flush=True)
                    return "fallback_lookup_unavailable"
                if created < slot:
                    older_than_slot = True
                    continue
                if created > now:
                    continue
                if run.get("status") != "completed":
                    # Operational odds runs share a serialized concurrency group.
                    # An overlapping in-progress run here belongs to another
                    # group (for example, an ineligible PR-origin no-op) and
                    # cannot prove that this slot is already being sampled.
                    continue
                if run.get("conclusion") == "success":
                    run_id = run.get("id")
                    if type(run_id) is not int or run_id <= 0:
                        print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "page": page_seen, "runs_examined": runs_examined, "reason": "invalid_prior_run_id"}), flush=True)
                        return "fallback_lookup_unavailable"
                    stage = "prior_artifact"
                    if probe_check is None:
                        state = direct_probe_evidence(
                            repository, token, run_id, expected_slot=slot,
                            run_created_at=created)
                    else:
                        state = probe_check(repository, token, run_id)
                    if state == "unavailable":
                        print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "page": page_seen, "runs_examined": runs_examined, "artifact_state": state, "prior_run_id": run_id}), flush=True)
                    if state == "valid":
                        return "prior_fallback_observed"
                    if state != "no_valid_odds":
                        return "fallback_lookup_unavailable"
            if older_than_slot or len(runs) < 100:
                return "prior_fallback_absent_or_failed"
        # Five full pages with no older timestamp is an incomplete scan.
        print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": "history_page_limit", "page": page_seen, "runs_examined": runs_examined, "reason": "incomplete_scan"}), flush=True)
        return "fallback_lookup_unavailable"
    except (KeyError, TypeError, ValueError, OSError, TimeoutError, HTTPError, URLError) as exc:
        print("LIVE_ODDS_FALLBACK_DIAGNOSTIC " + json.dumps({"stage": stage, "page": page_seen, "runs_examined": runs_examined, "error_class": type(exc).__name__, "http_status": exc.code if isinstance(exc, HTTPError) else None}), flush=True)
        return "fallback_lookup_unavailable"


def main():
    trigger = event_provenance()
    event = trigger["event"]
    allowed = eligible(event, trigger)
    schedule_guard = "not_applicable"
    if allowed and event == "workflow_run":
        schedule_guard = direct_schedule_guard(
            trigger, os.environ.get("GITHUB_REPOSITORY", ""),
            os.environ.get("GH_TOKEN", ""))
        allowed = schedule_guard == "direct_schedule_absent_or_failed"
        if allowed:
            schedule_guard = prior_fallback_guard(
                trigger, os.environ.get("GITHUB_REPOSITORY", ""),
                os.environ.get("GH_TOKEN", ""),
                int(os.environ.get("GITHUB_RUN_ID", "0") or 0))
            allowed = schedule_guard == "prior_fallback_absent_or_failed"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fp:
            fp.write("collect=" + str(allowed).lower() + "\n")
    if not allowed:
        now = datetime.now(timezone.utc)
        data = {
            "checked_at_jst": now.astimezone(timezone(timedelta(hours=9))).isoformat(),
            "source_status": "fallback_ineligible",
            "trigger": trigger,
            "samples": [],
            "reason": schedule_guard if event == "workflow_run" else "upstream_not_verified_or_outside_bounded_fallback_window",
        }
        Path("live_odds_metrics.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_ODDS_TRIGGER_GATE " + json.dumps({
        "collect": allowed, "source": event,
        "upstream_event": trigger.get("upstream_event"),
        "upstream_run_id": trigger.get("upstream_run_id"),
        "direct_schedule_guard": schedule_guard}), flush=True)


if __name__ == "__main__":
    main()
