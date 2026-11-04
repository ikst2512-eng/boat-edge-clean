"""Unit tests for 14-day live odds trend: exact denominators and no fabricated history."""
import importlib.util
import io
import json
import unittest
import zipfile
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "history", Path(__file__).resolve().parents[1] / "scripts/summarize_live_odds_history.py"
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


def race(code, states, elapsed=800):
    codes = {"valid_200": 200, "pending_202": 202, "http_error": 503,
             "invalid_200": 200, "transport_error:TimeoutError": None}
    return {"race_code": code, "attempts": [
        {"http": codes.get(state), "state": state, "latency_ms": 100 * (i+1)}
        for i, state in enumerate(states)], "elapsed_ms": elapsed}


class OddsHistoryTests(unittest.TestCase):
    def test_timestamped_odds_must_belong_to_run_start(self):
        steps = race("202611030111", ["valid_200"])["attempts"]
        steps[0].update(started_at_utc="2026-11-03T03:25:05+00:00",
                        finished_at_utc="2026-11-03T03:25:06+00:00")
        self.assertTrue(history.consistent_observation_times(
            steps, "2026-11-03T12:25:00+09:00"))
        self.assertFalse(history.consistent_observation_times(
            steps, "2026-11-03T14:25:00+09:00"))
        self.assertFalse(history.consistent_observation_times(
            steps, "2026-11-02T12:25:00+09:00"))
        self.assertFalse(history.consistent_observation_times(steps, None))
        self.assertFalse(history.consistent_observation_times(
            steps, "2026-11-03T12:25:00"))
        # Old artifact remains classifiable but does not prove precise timing.
        self.assertTrue(history.consistent_observation_times(
            race("202611030111", ["valid_200"])["attempts"], None))

    def test_history_rejects_timestamped_200_from_different_run(self):
        sample = race("202611030111", ["valid_200"])
        sample["attempts"][0].update(
            started_at_utc="2026-11-03T03:25:05+00:00",
            finished_at_utc="2026-11-03T03:25:06+00:00")
        record = {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                  "samples": [sample]}
        self.assertEqual(history.summarize([record])["eventual_valid_races"], 0)
        record["checked_at_jst"] = "2026-11-03T12:25:00+09:00"
        self.assertEqual(history.summarize([record])["eventual_valid_races"], 1)

    def test_legacy_odds_artifacts_without_attempt_timestamps_remain_eligible(self):
        self.assertTrue(history.consistent_attempts(
            race("202611030111", ["pending_202", "valid_200"])["attempts"]))

    def test_new_odds_timestamps_must_be_complete_utc_and_chronological(self):
        steps = race("202611030111", ["pending_202", "valid_200"])["attempts"]
        steps[0].update(started_at_utc="2026-11-03T03:25:00+00:00",
                        finished_at_utc="2026-11-03T03:25:01+00:00")
        steps[1].update(started_at_utc="2026-11-03T03:25:02+00:00",
                        finished_at_utc="2026-11-03T03:25:03+00:00")
        self.assertTrue(history.consistent_attempts(steps))
        malformed = [dict(item) for item in steps]
        del malformed[1]["finished_at_utc"]
        self.assertFalse(history.consistent_attempts(malformed))
        malformed = [dict(item) for item in steps]
        malformed[1]["started_at_utc"] = "2026-11-03T03:25:00+00:00"
        self.assertFalse(history.consistent_attempts(malformed))
        malformed = [dict(item) for item in steps]
        malformed[0]["started_at_utc"] = "2026-11-03T03:26:00+00:00"
        self.assertFalse(history.consistent_attempts(malformed))
        malformed = [dict(item) for item in steps]
        malformed[0]["finished_at_utc"] = "2026-11-03T12:25:01+09:00"
        self.assertFalse(history.consistent_attempts(malformed))
        malformed = [dict(item) for item in steps]
        malformed[0]["finished_at_utc"] = "not-a-timestamp"
        self.assertFalse(history.consistent_attempts(malformed))

    def test_invalid_new_timestamp_evidence_is_not_counted(self):
        sample = race("202611030111", ["valid_200"])
        sample["attempts"][0]["started_at_utc"] = "2026-11-03T03:25:00+00:00"
        record = {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
                  "samples": [sample]}
        self.assertEqual(history.summarize([record])["eventual_valid_races"], 0)

    def test_count_valid_pending_recovered_and_errors_without_duplicating(self):
        data = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"]),
                         race("202611030112", ["pending_202", "valid_200"], 2300),
                         race("202611030113", ["pending_202", "pending_202", "pending_202"], 4500)]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
             "samples": [race("202611030111", ["http_error"]),
                         race("202611030114", ["invalid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"])]},
        ]
        m = history.summarize(data)
        self.assertEqual(m["race_observations"], 5)
        self.assertEqual(m["unique_races"], 4)
        self.assertEqual(m["runs_with_eligible_observations"], 2)
        self.assertEqual(m["requests"], 8)
        self.assertEqual(m["http_200"], 3)
        self.assertEqual(m["http_202"], 4)
        self.assertEqual(m["http_503"], 1)
        self.assertEqual(m["first_attempt_valid_races"], 1)
        self.assertEqual(m["eventual_valid_races"], 2)
        self.assertEqual(m["eventual_valid_rate_pct"], 40.0)
        self.assertEqual(m["initially_pending_races"], 2)
        self.assertEqual(m["pending_recovered"], 1)
        self.assertEqual(m["pending_recovery_rate_pct"], 50.0)

    def test_daily_trend_missing_days_are_not_successes(self):
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        data = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race("202611030111", ["valid_200"]),
                         race("202611030112", ["pending_202", "valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-02T14:25:00+09:00",
             "samples": [race("202611020111", ["pending_202", "pending_202", "pending_202"])]},
            {"source_status": "ok", "checked_at_jst": "2026-10-01T14:25:00+09:00",
             "samples": [race("202610010111", ["valid_200"])]},
        ]
        rows = history.daily_trends(data, now=now)
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[-1]["date_jst"], "2026-11-03")
        self.assertEqual(rows[-1]["valid_rate_pct"], 100.0)
        self.assertEqual(rows[-1]["pending_recovery_rate_pct"], 100.0)
        self.assertEqual(rows[-2]["date_jst"], "2026-11-02")
        self.assertEqual(rows[-2]["valid_rate_pct"], 0.0)
        self.assertEqual(rows[-2]["pending_recovery_rate_pct"], 0.0)
        self.assertEqual(sum(row["has_valid_observations"] for row in rows), 2)
        self.assertIsNone(rows[0]["valid_rate_pct"])
        self.assertIsNone(rows[0]["pending_recovery_rate_pct"])

    def test_daily_trend_rejects_naive_future_and_invalid_timestamps(self):
        from datetime import timezone, timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 14, 0, tzinfo=jst)
        rows = history.daily_trends([
            {"source_status": "ok", "checked_at_jst": "2026-11-04T12:25:00+09:00",
             "samples": [race("202611040111", ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00",
             "samples": [race("202611030111", ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "invalid",
             "samples": [race("202611030112", ["valid_200"])]},
        ], now=now)
        self.assertTrue(all(not row["has_valid_observations"] for row in rows))

    def test_no_observations_is_not_success(self):
        m = history.summarize([{"source_status": "no_upcoming_race", "checked_at_jst": "x", "samples": []}])
        self.assertEqual(m["race_observations"], 0)
        self.assertIsNone(m["eventual_valid_rate_pct"])
        self.assertIsNone(m["pending_recovery_rate_pct"])
        self.assertIsNone(m["median_request_latency_ms"])

    def test_exclude_invalid_evidence(self):
        m = history.summarize([{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                                "samples": [race("bad", ["valid_200"]),
                                            race("202611030111", ["fake_success"])]}])
        self.assertEqual(m["race_observations"], 0)

    def test_load_prior_scheduled_artifact_from_zip(self):
        record = {"checked_at_jst": "2026-11-03T13:00:00+09:00", "source_status": "ok",
                  "samples": [race("202611030111", ["valid_200"])]}
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as zf:
            zf.writestr(history.FILE, json.dumps(record))
        fake_run = {"id": 42, "event": "schedule", "conclusion": "success",
                    "created_at": "2026-11-03T04:00:00Z"}
        def fake_api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [fake_run] if "&event=schedule&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 7, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(archive_bytes.getvalue())):
            rows, selected, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake", {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(selected, 1)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(history.summarize(rows)["eventual_valid_races"], 1)

    def test_history_zip_redirect_never_carries_bearer(self):
        from urllib.error import HTTPError
        from urllib.request import HTTPRedirectHandler
        fake_run = {"id": 84, "event": "schedule", "conclusion": "success",
                    "created_at": "2026-11-03T04:00:00Z"}
        def api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [fake_run] if "&event=schedule&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 8, "expired": False}]}

        requests = []
        def archive(request, **_):
            requests.append(request)
            redirected = HTTPRedirectHandler().redirect_request(
                request, None, 302, "Found", {},
                "https://artifact-cdn.example.test/file.zip?sig=test")
            self.assertIn("Authorization", request.unredirected_hdrs)
            self.assertNotIn("Authorization", request.headers)
            self.assertNotIn("Authorization", redirected.headers)
            self.assertNotIn("Authorization", redirected.unredirected_hdrs)
            raise HTTPError("https://artifact-cdn.example.test", 401, "Unauthorized", None, None)

        with patch.object(history, "api_json", side_effect=api), patch.object(
                history, "urlopen", side_effect=archive):
            rows, selected, errors = history.fetch_history(
                "a/b", "fake", {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, tzinfo=timezone.utc))
        self.assertEqual(selected, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(requests), 1)
        self.assertEqual(errors[0]["http_status"], 401)

    def test_history_artifact_http_errors_keep_stage_and_status(self):
        from urllib.error import HTTPError

        fake_run = {"id": 52, "event": "schedule", "conclusion": "success",
                    "created_at": "2026-11-03T04:00:00Z"}

        def api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [fake_run] if "&event=schedule&" in url else []}
            if "/artifacts?" in url:
                raise HTTPError(url, 403, "Forbidden", None, None)
            raise AssertionError(url)

        with patch.object(history, "api_json", side_effect=api):
            rows, selected, errors = history.fetch_history(
                "a/b", "fake", {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, tzinfo=timezone.utc))
        self.assertEqual(selected, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors, [{"run_id": 52, "status": "HTTPError",
                                   "stage": "artifact_metadata", "http_status": 403}])

        def metadata(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [fake_run] if "&event=schedule&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 8, "expired": False}]}

        def zip_failure(*_args, **_kwargs):
            raise HTTPError("https://example.test/zip", 404, "Missing", None, None)

        with patch.object(history, "api_json", side_effect=metadata), patch.object(
                history, "urlopen", side_effect=zip_failure):
            rows, selected, errors = history.fetch_history(
                "a/b", "fake", {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, tzinfo=timezone.utc))
        self.assertEqual(selected, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors, [{"run_id": 52, "status": "HTTPError",
                                   "stage": "artifact_zip", "http_status": 404}])

    def test_invalid_same_race_run_does_not_inflate_eligible_runs(self):
        code = "202611030111"
        rows = [
            {"source_status": "ok", "checked_at_jst": "2026-11-03T12:25:00+09:00",
             "samples": [race(code, ["valid_200"])]},
            {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
             "samples": [race(code, ["fake_success"])]},
        ]
        result = history.summarize(rows)
        self.assertEqual(result["runs_with_eligible_observations"], 1)
        self.assertEqual(result["race_observations"], 1)

    def test_all_42_scheduled_runs_are_inside_history_capacity(self):
        self.assertGreaterEqual(history.MAX_RUNS, 42)

    def test_reject_http_status_and_retry_state_contradictions(self):
        code = "202611030111"
        valid = race(code, ["valid_200"])
        mismatched = race("202611030112", ["valid_200"])
        mismatched["attempts"][0]["http"] = 202
        impossible = race("202611030113", ["valid_200", "pending_202"])
        transport = race("202611030114", ["transport_error:TimeoutError"])
        transport["attempts"][0]["http"] = 200
        false_pending = race("202611030115", ["pending_202"])
        false_pending["attempts"][0]["http"] = 200
        rows = [{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                 "samples": [valid, mismatched, impossible, transport, false_pending]}]
        m = history.summarize(rows)
        self.assertEqual(m["race_observations"], 1)
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["http_202"], 0)
        self.assertEqual(m["http_200"], 1)

    def test_initial_timeout_retry_is_valid_evidence(self):
        recovered = race("202611030116", ["transport_error:TimeoutError", "valid_200"])
        expired = race("202611030117", ["transport_error:TimeoutError",
                                        "transport_error:TimeoutError"])
        self.assertTrue(history.consistent_attempts(recovered["attempts"]))
        self.assertTrue(history.consistent_attempts(expired["attempts"]))
        m = history.summarize([{"source_status": "ok",
                               "checked_at_jst": "2026-11-03T14:25:00+09:00",
                               "samples": [recovered, expired]}])
        self.assertEqual(m["race_observations"], 2)
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["other_http_or_transport"], 3)

    def test_timeout_after_pending_or_after_second_attempt_cannot_retry(self):
        invalid_sequences = [
            ["pending_202", "transport_error:TimeoutError", "valid_200"],
            ["transport_error:TimeoutError", "transport_error:TimeoutError", "valid_200"],
            ["valid_200", "transport_error:TimeoutError"],
            ["http_error", "valid_200"],
        ]
        for states in invalid_sequences:
            with self.subTest(states=states):
                self.assertFalse(history.consistent_attempts(
                    race("202611030118", states)["attempts"]))

    def test_valid_pending_recovery_and_http_error_still_count(self):
        rows = [{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                 "samples": [race("202611030111", ["pending_202", "valid_200"]),
                             race("202611030112", ["http_error"]),
                             race("202611030113", ["transport_error:TimeoutError"])]}]
        m = history.summarize(rows)
        self.assertEqual(m["race_observations"], 3)
        self.assertEqual(m["pending_recovered"], 1)
        self.assertEqual(m["other_http_or_transport"], 1)
        self.assertEqual(m["http_503"], 1)

    def test_jst_first_calendar_day_and_failed_run_are_accounted_for(self):
        # At 14:00 JST Nov 3, Oct 21 00:30 JST is still within 14 calendar days.
        current = {"source_status": "no_upcoming_race", "samples": []}
        valid_stamp = "2026-10-21T00:30:00+09:00"
        early = {"id": 77, "event": "schedule", "conclusion": "success",
                 "created_at": "2026-10-20T15:30:00Z"}
        failed = {"id": 78, "event": "schedule", "conclusion": "failure",
                  "created_at": "2026-11-02T05:25:00Z"}
        evidence = {"checked_at_jst": valid_stamp, "source_status": "ok",
                    "samples": [race("202610210111", ["valid_200"])]}
        binary = io.BytesIO()
        with zipfile.ZipFile(binary, "w") as zf:
            zf.writestr(history.FILE, json.dumps(evidence))
        def fake_api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [early, failed] if "&event=schedule&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 123, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(binary.getvalue())):
            records, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake", current,
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(count, 2)
        self.assertEqual(len(records), 2)
        self.assertEqual(errors, [{"run_id": 78, "status": "workflow_failure"}])
        self.assertEqual(history.summarize(records)["eventual_valid_races"], 1)

    def test_future_dated_artifact_not_accepted(self):
        current = {"source_status": "no_upcoming_race", "samples": []}
        run = {"id": 8, "event": "schedule", "conclusion": "success",
               "created_at": "2026-11-03T04:00:00Z"}
        evidence = {"checked_at_jst": "2026-11-04T13:00:00+09:00",
                    "source_status": "ok", "samples": [race("202611040111", ["valid_200"])]}
        binary = io.BytesIO()
        with zipfile.ZipFile(binary, "w") as zf:
            zf.writestr(history.FILE, json.dumps(evidence))
        with patch.object(history, "api_json", side_effect=lambda url, token: (
                {"workflow_runs": [run] if "&event=schedule&" in url else []} if "/runs?status=" in url else
                {"artifacts": [{"name": history.ARTIFACT, "id": 5, "expired": False}]})), patch.object(
                history, "urlopen", return_value=io.BytesIO(binary.getvalue())):
            records, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake", current,
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(errors, [{"run_id": 8, "status": "ValueError",
                                   "stage": "artifact_parse", "http_status": None}])

    def test_second_history_page_can_recover_older_scheduled_evidence(self):
        # A busy repo's first 100 entries can contain unrelated completed PR runs.
        recent_prs = [{"id": n, "event": "pull_request", "conclusion": "success",
                       "created_at": "2026-11-03T04:00:00Z"} for n in range(100)]
        older = {"id": 301, "event": "schedule", "conclusion": "success",
                 "created_at": "2026-11-02T05:25:00Z"}
        valid = {"checked_at_jst": "2026-11-02T14:25:01+09:00",
                 "source_status": "ok", "samples": [race("202611020111", ["valid_200"])]}
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as zf:
            zf.writestr(history.FILE, json.dumps(valid))
        requested = []
        def fake_api(url, token):
            if "/runs?status=" in url:
                requested.append(url)
                return {"workflow_runs": recent_prs if "&page=1" in url else [older]}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 7, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(payload.getvalue())):
            records, selected, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(len(requested), 4)
        self.assertEqual(selected, 1)
        self.assertEqual(errors, [])
        self.assertEqual(history.summarize(records)["eventual_valid_races"], 1)

    def test_fallback_volume_isolated_from_direct_scheduled_event_pages(self):
        import datetime
        t = datetime.datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc)
        direct = {"id": 77, "event": "schedule", "conclusion": "failure",
                  "created_at": "2026-11-03T03:25:00Z"}
        noisy = [{"id": n, "event": "workflow_run", "conclusion": "success",
                  "created_at": "2026-11-03T02:00:00Z"} for n in range(100)]
        seen = []
        def fake_api(url, token):
            if "/runs?status=" in url:
                seen.append(url)
                if "&event=schedule&" in url:
                    return {"workflow_runs": [direct]}
                if "&event=workflow_run&" in url:
                    return {"workflow_runs": noisy if "&page=1" in url else []}
                return {"workflow_runs": []}
            return {"artifacts": []}
        with patch.object(history, "api_json", side_effect=fake_api):
            records, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []}, now=t)
        self.assertEqual(count, 1)
        self.assertEqual(errors, [{"run_id": 77, "status": "workflow_failure"}])
        self.assertEqual(len(records), 1)
        self.assertTrue(any("&event=schedule&" in u for u in seen))
        self.assertTrue(any("&event=workflow_run&" in u for u in seen))

    def test_fallback_time_prefilter_retains_delayed_bounded_event(self):
        from datetime import timezone
        self.assertTrue(history.plausible_fallback_run_time(
            datetime.fromisoformat("2026-11-03T06:20:00+00:00")))
        self.assertFalse(history.plausible_fallback_run_time(
            datetime.fromisoformat("2026-11-03T02:00:00+00:00")))

    def test_unread_final_page_must_be_flagged_incomplete(self):
        rows = [{"id": n, "event": "pull_request", "conclusion": "success",
                 "created_at": "2026-11-03T04:00:00Z"} for n in range(100)]
        with patch.object(history, "MAX_PAGES", 1), patch.object(
                history, "api_json", return_value={"workflow_runs": rows}):
            records, selected, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc))
        self.assertEqual(selected, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(errors, [{"run_id": None, "status": "workflow_run_list_truncated"}])

    def test_missing_scheduled_trigger_after_grace_is_not_success(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 15, 2, tzinfo=jst)
        old = {"id": 19, "event": "schedule", "status": "completed",
               "conclusion": "success", "created_at": "2026-11-02T11:25:39Z"}
        data = history.schedule_trigger_health([old], now=now)
        self.assertEqual([x["scheduled_jst"] for x in data["slots"]],
                         ["2026-11-03T12:25:00+09:00",
                          "2026-11-03T14:25:00+09:00",
                          "2026-11-03T16:25:00+09:00"])
        self.assertEqual([x["state"] for x in data["slots"]],
                         ["not_observed_after_grace", "awaiting_grace", "awaiting_grace"])
        self.assertEqual(data["not_observed_after_grace"], 1)
        self.assertEqual(data["observed_slots"], 0)

    def test_hours_late_direct_schedule_is_reported_without_slot_credit(self):
        jst = timezone(__import__("datetime").timedelta(hours=9))
        now = datetime(2026, 11, 3, 20, 15, tzinfo=jst)
        late = {"id": 41624217156, "event": "schedule",
                "status": "completed", "conclusion": "success",
                "created_at": "2026-11-03T11:02:28Z"}
        result = history.schedule_trigger_health([late], now=now)
        self.assertEqual(result["observed_slots"], 0)
        self.assertEqual(result["not_observed_after_grace"], 3)
        self.assertEqual(result["outside_grace_unattributed_runs"], [{
            "run_id": 41624217156, "created_at": "2026-11-03T11:02:28Z",
            "conclusion": "success", "status": "completed"}])

    def test_in_window_schedule_is_not_misreported_as_unattributed(self):
        jst = timezone(__import__("datetime").timedelta(hours=9))
        now = datetime(2026, 11, 3, 16, 30, tzinfo=jst)
        scheduled = {"id": 11, "event": "schedule", "status": "completed",
                     "conclusion": "success", "created_at": "2026-11-03T05:25:10Z"}
        result = history.schedule_trigger_health([scheduled], now=now)
        self.assertEqual(result["observed_slots"], 1)
        self.assertEqual(result["outside_grace_unattributed_runs"], [])

    def test_observed_schedule_event_requires_correct_slot(self):
        jst = timezone(__import__("datetime").timedelta(hours=9))
        now = datetime(2026, 11, 3, 15, 2, tzinfo=jst)
        observed = {"id": 28, "event": "schedule", "status": "completed",
                    "conclusion": "success", "created_at": "2026-11-03T03:41:00Z"}
        not_schedule = {"id": 29, "event": "pull_request", "status": "completed",
                        "conclusion": "success", "created_at": "2026-11-03T05:25:00Z"}
        data = history.schedule_trigger_health([observed, not_schedule], now=now)
        self.assertEqual(data["observed_slots"], 1)
        self.assertEqual(data["not_observed_after_grace"], 0)
        self.assertEqual(len(data["slots"][0]["matching_runs"]), 1)
        self.assertEqual(data["slots"][1]["state"], "awaiting_grace")

    def test_14day_schedule_history_marks_missing_trigger_separately(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 15, 6, tzinfo=jst)
        runs = [
            {"id": 8, "event": "schedule", "status": "completed",
             "conclusion": "success", "created_at": "2026-11-02T03:26:00Z"},
            {"id": 9, "event": "pull_request", "status": "completed",
             "conclusion": "success", "created_at": "2026-11-03T03:26:00Z"},
        ]
        report = history.schedule_history_coverage(runs, now=now)
        self.assertEqual(report["calendar_days"], 14)
        self.assertEqual(report["slots_configured"], 42)
        self.assertEqual(report["observed_slots"], 1)
        self.assertEqual(report["not_observed_after_grace"], 39)
        self.assertEqual(report["awaiting_grace"], 2)
        self.assertEqual(report["daily"][-1]["date_jst"], "2026-11-03")
        self.assertEqual([slot["state"] for slot in report["daily"][-1]["slots"]],
                         ["not_observed_after_grace", "awaiting_grace", "awaiting_grace"])
        self.assertEqual(report["daily"][-2]["observed_slots"], 1)
        self.assertEqual(report["observed_rate_pct"], 2.5)

    def test_14day_schedule_history_only_counts_matured_slots(self):
        from datetime import timedelta
        now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone(timedelta(hours=9)))
        report = history.schedule_history_coverage([], now=now, days=1)
        self.assertEqual(report["observed_slots"], 0)
        self.assertEqual(report["not_observed_after_grace"], 0)
        self.assertEqual(report["awaiting_grace"], 3)
        self.assertIsNone(report["observed_rate_pct"])

    def test_repository_creation_boundary_is_not_a_missed_schedule(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 16, 19, tzinfo=jst)
        created = datetime(2026, 10, 22, 18, 24, tzinfo=jst)
        rows = history.schedule_history_coverage([], now=now, earliest_possible=created)
        self.assertEqual(rows["slots_configured"], 42)
        self.assertEqual(rows["slots_before_repository_creation"], 6)
        self.assertEqual(rows["eligible_slots"], 36)
        self.assertEqual(rows["awaiting_grace"], 1)
        self.assertEqual(rows["not_observed_after_grace"], 35)
        self.assertTrue(all(s["state"] == "before_repository_creation"
                            for r in rows["daily"][:2] for s in r["slots"]))

    def test_repository_created_at_is_used_for_live_schedule_history(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 16, 19, tzinfo=jst)
        def fake_api(url, token):
            if "/runs?event=schedule" in url:
                return {"workflow_runs": []}
            return {"created_at": "2026-10-22T09:24:01Z"}
        with patch.object(history, "api_json", side_effect=fake_api):
            report = history.fetch_schedule_trigger_health("a/b", "token", now=now)
        self.assertEqual(report["history_14day"]["slots_before_repository_creation"], 6)
        self.assertEqual(report["history_14day"]["slots_before_schedule_enabled"], 26)
        self.assertEqual(report["history_14day"]["eligible_slots"], 10)
        self.assertEqual(report["history_14day"]["not_observed_after_grace"], 9)
        self.assertEqual(report["not_observed_after_grace"], 2)
        self.assertEqual(report["history_14day"]["awaiting_grace"], 1)
        self.assertEqual(report["schedule_configured_at"], "2026-10-31T06:38:46+00:00")

    def test_schedule_coverage_excludes_slots_before_workflow_existed(self):
        from datetime import timedelta
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 3, 17, 40, tzinfo=jst)
        configured = datetime(2026, 10, 31, 15, 38, 46, tzinfo=jst)
        created = datetime(2026, 10, 22, 18, 24, tzinfo=jst)
        coverage = history.schedule_history_coverage(
            [], now=now, earliest_possible=created, schedule_configured_at=configured)
        self.assertEqual(coverage["slots_configured"], 42)
        self.assertEqual(coverage["slots_before_repository_creation"], 6)
        self.assertEqual(coverage["slots_before_schedule_enabled"], 26)
        self.assertEqual(coverage["eligible_slots"], 10)
        self.assertEqual(coverage["not_observed_after_grace"], 9)
        self.assertEqual(coverage["awaiting_grace"], 1)
        oct31 = next(row for row in coverage["daily"] if row["date_jst"] == "2026-10-31")
        self.assertEqual([slot["state"] for slot in oct31["slots"]],
                         ["before_schedule_enabled", "before_schedule_enabled",
                          "not_observed_after_grace"])

    def test_operational_event_eligibility_excludes_pr(self):
        for event in ("pull_request", "workflow_dispatch", "push", "", "unknown"):
            self.assertFalse(history.include_current_event(event))
        self.assertTrue(history.include_current_event("schedule"))

    def test_manual_dispatch_is_neither_current_nor_historical_unattended_evidence(self):
        now = datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc)
        seen = []
        def fake_api(url, token):
            seen.append(url)
            return {"workflow_runs": []}
        with patch.object(history, "api_json", side_effect=fake_api):
            rows, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []}, now=now)
        self.assertEqual(count, 0)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertFalse(history.include_current_event("workflow_dispatch"))
        self.assertFalse(any("&event=workflow_dispatch&" in url for url in seen))
        self.assertTrue(any("&event=schedule&" in url for url in seen))
        self.assertTrue(any("&event=workflow_run&" in url for url in seen))

    def test_pr_current_200_not_part_of_trend(self):
        import os
        import tempfile
        current = {"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                   "samples": [race("202611030111", ["valid_200"])]}
        prior = {"source_status": "ok", "checked_at_jst": "2026-11-02T14:25:00+09:00",
                 "samples": [race("202611020111", ["pending_202", "pending_202", "pending_202"])]}
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                Path(history.FILE).write_text(json.dumps(current), encoding="utf-8")
                env = {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_REPOSITORY": "test/repo",
                       "GH_TOKEN": "token", "GITHUB_STEP_SUMMARY": ""}
                with patch.dict(os.environ, env), patch.object(
                        history, "fetch_history", return_value=([current, prior], 1, [])), patch.object(
                        history, "fetch_schedule_trigger_health", return_value={}):
                    history.main()
                result = json.loads(Path("live_odds_14day_trend.json").read_text())
                self.assertFalse(result["includes_current_run"])
                self.assertEqual(result["source_event"], "pull_request")
                self.assertEqual(result["history_evidence_loaded"], 1)
                self.assertEqual(result["metrics"]["race_observations"], 1)
                self.assertEqual(result["metrics"]["eventual_valid_races"], 0)
                self.assertEqual(result["metrics"]["http_202"], 3)
            finally:
                os.chdir(cwd)

    def test_fallback_only_trusted_scheduled_upstream_enters_monitoring(self):
        base = {"event": "workflow_run", "upstream_event": "schedule",
                "upstream_workflow": "CLEAN prospective pre-cutoff capture",
                "upstream_branch": "main", "upstream_run_id": 42}
        record = {"trigger": base}
        self.assertTrue(history.include_current_event("workflow_run", record))
        secondary = {**base, "upstream_workflow": "Four-mode prospective capture (research only)"}
        self.assertTrue(history.include_current_event("workflow_run", {"trigger": secondary}))
        self.assertFalse(history.include_current_event("pull_request", record))
        for key, value in (("upstream_event", "pull_request"),
                           ("upstream_workflow", "Some other workflow"),
                           ("upstream_branch", "feature"),
                           ("upstream_run_id", None)):
            changed = dict(base)
            changed[key] = value
            self.assertFalse(history.include_current_event("workflow_run", {"trigger": changed}))

    def test_ineligible_fallback_artifact_does_not_raise_missing_evidence(self):
        record = {"checked_at_jst": "2026-11-03T14:50:00+09:00",
                  "source_status": "fallback_ineligible",
                  "trigger": {"event": "workflow_run", "upstream_event": "push",
                              "upstream_workflow": "CLEAN prospective pre-cutoff capture",
                              "upstream_branch": "main", "upstream_run_id": 123},
                  "samples": []}
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr(history.FILE, json.dumps(record))
        upstream = {"id": 999, "event": "workflow_run", "conclusion": "success",
                    "created_at": "2026-11-03T05:45:00Z"}
        def fake_api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [upstream] if "&event=workflow_run&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 77, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(archive.getvalue())):
            records, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc))
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])
        self.assertEqual(history.summarize(records)["race_observations"], 0)

    def test_prior_verified_scheduled_fallback_artifact_enters_trend(self):
        record = {"checked_at_jst": "2026-11-03T14:50:00+09:00",
                  "source_status": "ok",
                  "trigger": {"event": "workflow_run", "upstream_event": "schedule",
                              "upstream_workflow": "CLEAN prospective pre-cutoff capture",
                              "upstream_branch": "main", "upstream_run_id": 123},
                  "samples": [race("202611030111", ["valid_200"])]}
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr(history.FILE, json.dumps(record))
        upstream = {"id": 999, "event": "workflow_run", "conclusion": "success",
                    "created_at": "2026-11-03T05:45:00Z"}
        def fake_api(url, token):
            if "/runs?status=" in url:
                return {"workflow_runs": [upstream] if "&event=workflow_run&" in url else []}
            return {"artifacts": [{"name": history.ARTIFACT, "id": 77, "expired": False}]}
        with patch.object(history, "api_json", side_effect=fake_api), patch.object(
                history, "urlopen", return_value=io.BytesIO(archive.getvalue())):
            records, count, errors = history.fetch_history(
                "ikst2512-eng/boat-edge-clean", "fake",
                {"source_status": "no_upcoming_race", "samples": []},
                now=datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc))
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])
        self.assertEqual(history.summarize(records)["eventual_valid_races"], 1)

    def test_first_200_does_not_count_as_recovery(self):
        m = history.summarize([{"source_status": "ok", "checked_at_jst": "2026-11-03T14:25:00+09:00",
                                "samples": [race("202611030111", ["valid_200"])]}])
        self.assertEqual(m["eventual_valid_races"], 1)
        self.assertEqual(m["pending_recovered"], 0)
        self.assertIsNone(m["pending_recovery_rate_pct"])


if __name__ == "__main__":
    unittest.main()
