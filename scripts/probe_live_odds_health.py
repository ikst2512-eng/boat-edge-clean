"""Bounded, result-blind live odds availability/latency audit.

Only independently sourced upcoming races. A returned HTTP 202 is never success.
No forecast model, saved prediction or result data is used.
"""
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from itertools import permutations
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXPECTED = {"-".join(map(str, t)) for t in permutations(range(1, 7), 3)}
BASE_URL = "https://boat-edge-clean.onrender.com"
USER_AGENT = "BOAT-EDGE-CLEAN-LIVE-ODDS-AUDIT/1.0"


def valid_odds(payload, race_code, now):
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    try:
        matching = (payload.get("hd") == race_code[:8] and
                    str(payload.get("jcd")).zfill(2) == race_code[8:10] and
                    int(payload.get("rno") or 0) == int(race_code[10:12]))
    except (ValueError, TypeError):
        return False
    if not matching:
        return False
    odds = payload.get("odds")
    if not isinstance(odds, dict) or set(odds) != EXPECTED:
        return False
    if not all(type(value) in (int, float) and 1 <= value <= 1_000_000 for value in odds.values()):
        return False
    try:
        fetched = datetime.fromisoformat(payload["fetched_at"])
        return fetched.tzinfo is not None and -300 <= (now - fetched).total_seconds() <= 1800
    except (KeyError, TypeError, ValueError):
        return False


def sample_race(code, *, request=urlopen, clock=time.monotonic, pause=time.sleep, now=None):
    now = now or datetime.now(timezone.utc)
    url = BASE_URL + "/api/odds?hd=" + code[:8] + "&jcd=" + code[8:10] + "&rno=" + str(int(code[10:12]))
    attempts = []
    total_start = clock()
    for attempt in range(3):
        start = clock()
        try:
            with request(Request(url, headers={"User-Agent": USER_AGENT}), timeout=25) as response:
                status = response.status
                raw = response.read(200000)
            payload = json.loads(raw)
            state = ("valid_200" if valid_odds(payload, code, now) else "invalid_200") if status == 200 else ("pending_202" if status == 202 else "other_http")
        except HTTPError as error:
            status = error.code
            state = "pending_202" if status == 202 else "http_error"
        except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError, TypeError) as error:
            status = None
            state = "transport_error:" + type(error).__name__
        attempts.append({"http": status, "state": state, "latency_ms": round((clock() - start) * 1000)})
        if state != "pending_202" or attempt == 2:
            break
        pause(2)
    return {"race_code": code, "attempts": attempts, "final_state": attempts[-1]["state"],
            "elapsed_ms": round((clock() - total_start) * 1000)}


def select_candidates(titles, day, now, jst):
    candidates = []
    for row in titles:
        code = row.get("レースコード", "")
        deadline = row.get("電話投票締切予定", "")
        if not isinstance(code, str) or len(code) != 12 or not code.isdigit() or not code.startswith(day):
            continue
        try:
            close = datetime.strptime(day + deadline, "%Y%m%d%H:%M").replace(tzinfo=jst)
        except (ValueError, TypeError):
            continue
        if now + timedelta(minutes=8) < close < now + timedelta(hours=3):
            candidates.append((close, code))
    return [code for _, code in sorted(set(candidates))[:3]]


def summarize(samples):
    requests = [step for item in samples for step in item["attempts"]]
    timings = [item["elapsed_ms"] for item in samples]
    counts = {str(status): sum(step["http"] == status for step in requests) for status in (200, 202, 503)}
    final_states = {}
    for item in samples:
        final_states[item["final_state"]] = final_states.get(item["final_state"], 0) + 1
    initially_pending = [item for item in samples if item["attempts"] and item["attempts"][0]["state"] == "pending_202"]
    recovered = [item for item in initially_pending if item["final_state"] == "valid_200"]
    exhausted = [item for item in initially_pending if item["final_state"] == "pending_202"]
    latencies = [step["latency_ms"] for step in requests]
    return {"races_sampled": len(samples), "requests": len(requests),
            "http_counts": counts, "non_200_202_503": len(requests) - sum(counts.values()),
            "final_states": final_states,
            "valid_200_races": final_states.get("valid_200", 0),
            "first_attempt_valid_races": sum(item["attempts"][0]["state"] == "valid_200" for item in samples if item["attempts"]),
            "initially_pending_races": len(initially_pending),
            "pending_recovered_to_valid_200": len(recovered),
            "pending_still_202": len(exhausted),
            "pending_recovery_rate_pct": round(100 * len(recovered) / len(initially_pending), 1) if initially_pending else None,
            "median_request_latency_ms": round(statistics.median(latencies)) if latencies else None,
            "median_race_elapsed_ms": round(statistics.median(timings)) if timings else None,
            "median_recovered_race_elapsed_ms": round(statistics.median(item["elapsed_ms"] for item in recovered)) if recovered else None}



def event_provenance():
    """Record actual workflow event and safe upstream identity in saved evidence."""
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    payload = {}
    try:
        path = os.environ.get("GITHUB_EVENT_PATH", "")
        if path:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError):
        payload = {}
    upstream = payload.get("workflow_run")
    if not isinstance(upstream, dict):
        upstream = {}
    return {
        "event": event,
        "cron": payload.get("schedule") if event == "schedule" else None,
        "upstream_event": upstream.get("event") if event == "workflow_run" else None,
        "upstream_workflow": upstream.get("name") if event == "workflow_run" else None,
        "upstream_branch": upstream.get("head_branch") if event == "workflow_run" else None,
        "upstream_run_id": upstream.get("id") if event == "workflow_run" else None,
        "upstream_created_at": upstream.get("created_at") if event == "workflow_run" else None,
    }


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from clean_openapi_sources import load
    from research_model import JST
    now = datetime.now(JST)
    day = now.strftime("%Y%m%d")
    data = {"checked_at_jst": now.isoformat(), "date": day, "scope": "live upcoming read-only odds",
            "sampling": "up to 3 upcoming races, at most 3 requests per race, 2s pending retry",
            "source_status": "unknown", "trigger": event_provenance(), "samples": []}
    try:
        titles, _, _, _, _ = load(day, now=now)
        codes = select_candidates(titles, day, now, JST)
        data["source_status"] = "ok" if codes else "no_upcoming_race"
        data["samples"] = [sample_race(code) for code in codes]
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as error:
        data["source_status"] = "unavailable:" + type(error).__name__
    data["summary"] = summarize(data["samples"])
    out = Path("live_odds_metrics.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = data["summary"]
    print("LIVE_ODDS_METRICS " + json.dumps({"source_status": data["source_status"], **summary}, ensure_ascii=False), flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("### Live odds availability (not prediction accuracy)\n\n")
            stream.write("Source: " + data["source_status"] + "\n\n")
            stream.write("Races sampled: " + str(summary["races_sampled"]) +
                         "; requests: " + str(summary["requests"]) +
                         "; valid HTTP 200 races: " + str(summary["valid_200_races"]) + "\n\n")
            stream.write("HTTP codes: " + json.dumps(summary["http_counts"]) + "\n\n")
            stream.write("First-attempt valid: " + str(summary["first_attempt_valid_races"]) +
                         "; initially HTTP 202: " + str(summary["initially_pending_races"]) +
                         "; recovered 202→valid 200: " + str(summary["pending_recovered_to_valid_200"]) +
                         "; exhausted 202: " + str(summary["pending_still_202"]) + "\n\n")
            stream.write("202 recovery rate (% of initially pending): " +
                         str(summary["pending_recovery_rate_pct"]) + "\n\n")
            stream.write("Median request latency (ms): " + str(summary["median_request_latency_ms"]) +
                         "; median race elapsed (ms): " + str(summary["median_race_elapsed_ms"]) +
                         "; median recovered race elapsed (ms): " + str(summary["median_recovered_race_elapsed_ms"]) + "\n\n")
            stream.write("No samples is not success. Full per-attempt evidence is in the artifact.\n")


if __name__ == "__main__":
    main()
