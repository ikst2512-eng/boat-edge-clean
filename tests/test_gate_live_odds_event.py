"""Fail-closed tests for scheduled-upstream odds fallback."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("gate_live_odds_event", SCRIPTS / "gate_live_odds_event.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class FallbackGateTests(unittest.TestCase):
    def test_workflow_concurrency_does_not_evict_scheduled_sampling(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/live-official-odds-probe.yml").read_text()
        self.assertIn("queue: max", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("github.event_name == 'pull_request'", workflow)
        self.assertIn("live-odds-pr-{0}", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("live-odds-manual-{0}", workflow)
        self.assertIn("github.event.workflow_run.event != 'schedule'", workflow)
        self.assertIn("live-odds-ineligible-", workflow)
        self.assertIn("live-odds-operational-", workflow)

    def test_primary_cron_has_exactly_three_original_jst_slots(self):
        # Split cron entries must retain the exact original daily times.
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/live-official-odds-probe.yml").read_text()
        import re
        cron = re.findall(r"^\\s+- cron: '([^']+)'", workflow, flags=re.MULTILINE)
        self.assertEqual(cron, ["25 3 * * *", "25 5 * * *", "25 7 * * *"])
        # UTC 03:25 / 05:25 / 07:25 are JST 12:25 / 14:25 / 16:25.
        self.assertEqual({(int(parts.split()[1]) + 9) % 24
                          for parts in cron}, {12, 14, 16})

    def test_only_approved_schedule_upstream_is_operational(self):
        from datetime import datetime, timezone
        allowed = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                   "upstream_run_id": 123, "upstream_created_at": "2026-11-03T03:45:00Z"}
        now = datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)
        self.assertTrue(gate.eligible("workflow_run", allowed, now=now))
        secondary = {**allowed, "upstream_workflow": gate.SECONDARY_UPSTREAM,
                     "upstream_created_at": "2026-11-03T07:38:00Z"}
        self.assertTrue(gate.eligible("workflow_run", secondary,
                                     now=datetime(2026, 11, 3, 7, 40, tzinfo=timezone.utc)))
        self.assertTrue(gate.eligible("schedule", {"event": "schedule"}))
        self.assertTrue(gate.eligible("workflow_dispatch", {"event": "workflow_dispatch"}))
        self.assertTrue(gate.eligible("pull_request", {"event": "pull_request"}))
        for key, val in (("upstream_event", "push"), ("upstream_event", "pull_request"),
                         ("upstream_branch", "feature"), ("upstream_workflow", "unknown"),
                         ("upstream_run_id", None)):
            bad = dict(allowed)
            bad[key] = val
            self.assertFalse(gate.eligible("workflow_run", bad, now=now))
        self.assertFalse(gate.eligible("workflow_run", {}))
        secondary["upstream_created_at"] = "2026-11-03T07:34:00Z"
        self.assertFalse(gate.eligible("workflow_run", secondary,
                                      now=datetime(2026, 11, 3, 7, 40, tzinfo=timezone.utc)))

    def test_fallback_only_in_three_jst_catchup_windows(self):
        from datetime import datetime, timezone, timedelta
        base = {"event": "workflow_run", "upstream_event": "schedule",
                "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                "upstream_run_id": 123}
        jst = timezone(timedelta(hours=9))
        for hour in (12, 14, 16):
            for minute in (40, 45, 54):
                source = datetime(2026, 11, 3, hour, minute, tzinfo=jst)
                trigger = {**base, "upstream_created_at": source.isoformat()}
                self.assertTrue(gate.eligible("workflow_run", trigger,
                                              now=source + timedelta(minutes=3)))
            for minute in (25, 30, 39, 55):
                source = datetime(2026, 11, 3, hour, minute, tzinfo=jst)
                trigger = {**base, "upstream_created_at": source.isoformat()}
                self.assertFalse(gate.eligible("workflow_run", trigger,
                                               now=source + timedelta(minutes=3)))
        for value in (None, "bad", "2026-11-03T12:45:00"):
            trigger = {**base, "upstream_created_at": value}
            self.assertFalse(gate.eligible("workflow_run", trigger,
                                           now=datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)))

    def test_reject_stale_and_future_fallback_upstream(self):
        from datetime import datetime, timezone, timedelta
        trigger = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                   "upstream_run_id": 123, "upstream_created_at": "2026-11-03T03:45:00Z"}
        source = datetime(2026, 11, 3, 3, 45, tzinfo=timezone.utc)
        self.assertFalse(gate.eligible("workflow_run", trigger, now=source - timedelta(seconds=1)))
        self.assertFalse(gate.eligible("workflow_run", trigger, now=source + timedelta(hours=2)))


    def test_direct_schedule_guard_avoids_duplicate_and_allows_failed_retry(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T03:45:00Z"}
        now = datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)
        direct = {"id": 17, "event": "schedule", "created_at": "2026-11-03T03:26:00Z",
                  "status": "completed", "conclusion": "success"}
        def fetch(url, token):
            self.assertIn("event=schedule", url)
            return {"workflow_runs": [direct]}
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                          fetch_json=fetch, probe_check=lambda *_: "valid"), "direct_schedule_observed")
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                          fetch_json=fetch, probe_check=lambda *_: "no_valid_odds"),
                         "direct_schedule_absent_or_failed")
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                          fetch_json=fetch, probe_check=lambda *_: "unavailable"),
                         "schedule_lookup_unavailable")
        direct["status"], direct["conclusion"] = "in_progress", None
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                                                    fetch_json=fetch), "direct_schedule_observed")
        direct["status"], direct["conclusion"] = "completed", "failure"
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                                                    fetch_json=fetch), "direct_schedule_absent_or_failed")
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                         fetch_json=lambda *_: {"workflow_runs": []}), "direct_schedule_absent_or_failed")


    def test_saved_artifact_with_verified_200_suppresses_fallback(self):
        import io
        import zipfile
        evidence = {"source_status": "ok", "samples": [{
            "race_code": "202611030111", "attempts": [{
                "http": 202, "state": "pending_202", "latency_ms": 80}, {
                "http": 200, "state": "valid_200", "latency_ms": 100}]}]}
        def archive_of(data):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as out:
                out.writestr("live_odds_metrics.json", json.dumps(data))
            return buffer.getvalue()
        artifacts = lambda *_: {"artifacts": [{"name": "live-odds-metrics", "id": 7, "expired": False}]}
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17, fetch_json=artifacts,
                          fetch_zip=lambda *_: archive_of(evidence)), "valid")
        pending = {"source_status": "ok", "samples": [{"race_code": "202611030111",
                    "attempts": [{"http": 202, "state": "pending_202", "latency_ms": 100}]}]}
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17, fetch_json=artifacts,
                          fetch_zip=lambda *_: archive_of(pending)), "no_valid_odds")
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17, fetch_json=artifacts,
                          fetch_zip=lambda *_: archive_of({"source_status": "unavailable:URLError",
                                                            "samples": []})), "no_valid_odds")
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17,
                          fetch_json=lambda *_: {"artifacts": []}), "no_valid_odds")
        evidence["samples"][0]["attempts"][-1]["http"] = 202
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17, fetch_json=artifacts,
                          fetch_zip=lambda *_: archive_of(evidence)), "no_valid_odds")

    def test_failed_artifact_download_does_not_assume_direct_success(self):
        artifacts = lambda *_: {"artifacts": [{"name": "live-odds-metrics", "id": 7, "expired": False}]}
        def inaccessible(*_):
            raise OSError("connection down")
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17,
                          fetch_json=artifacts, fetch_zip=inaccessible), "unavailable")
        self.assertEqual(gate.direct_probe_evidence("a/b", "token", 17,
                          fetch_json=lambda *_: {}), "unavailable")

    def test_direct_guard_fails_closed_for_unknown_api_status(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T03:45:00Z"}
        now = datetime(2026, 11, 3, 3, 50, tzinfo=timezone.utc)
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "", now=now),
                         "schedule_lookup_unavailable")
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                         fetch_json=lambda *_: {"workflow_runs": None}), "schedule_lookup_unavailable")
        def unavailable(*_):
            raise OSError("network unavailable")
        self.assertEqual(gate.direct_schedule_guard(trigger, "a/b", "token", now=now,
                         fetch_json=unavailable), "schedule_lookup_unavailable")

    def test_fallback_gate_writes_skipped_evidence_if_direct_cron_seen(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                trigger = {"event": "workflow_run", "upstream_event": "schedule",
                           "upstream_workflow": gate.UPSTREAM, "upstream_branch": "main",
                           "upstream_run_id": 123, "upstream_created_at": "2026-11-03T03:45:00Z"}
                with patch.dict(os.environ, {"GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "token",
                         "GITHUB_OUTPUT": str(Path(folder) / "out")}), patch.object(
                         gate, "event_provenance", return_value=trigger), patch.object(
                         gate, "eligible", return_value=True), patch.object(
                         gate, "direct_schedule_guard", return_value="direct_schedule_observed"):
                    gate.main()
                evidence = json.loads(Path("live_odds_metrics.json").read_text())
                self.assertEqual(evidence["source_status"], "fallback_ineligible")
                self.assertEqual(evidence["reason"], "direct_schedule_observed")
                self.assertEqual(evidence["samples"], [])
                self.assertIn("collect=false", Path("out").read_text())
            finally:
                os.chdir(old)

    def test_non_schedule_upstream_is_marked_ineligible_not_success(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                Path("event.json").write_text(json.dumps({"workflow_run": {
                    "id": 30, "event": "push", "name": gate.UPSTREAM, "head_branch": "main"}}))
                with patch.dict(os.environ, {
                    "GITHUB_EVENT_NAME": "workflow_run",
                    "GITHUB_EVENT_PATH": str(Path(folder) / "event.json"),
                    "GITHUB_OUTPUT": str(Path(folder) / "output")
                }):
                    gate.main()
                evidence = json.loads(Path("live_odds_metrics.json").read_text())
                self.assertEqual(evidence["source_status"], "fallback_ineligible")
                self.assertEqual(evidence["samples"], [])
                self.assertTrue(evidence["checked_at_jst"].endswith("+09:00"))
                self.assertIn("collect=false", Path("output").read_text())
            finally:
                os.chdir(old)


    def test_secondary_fallback_does_not_duplicate_verified_first_fallback(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T07:45:00Z"}
        now = datetime(2026, 11, 3, 7, 50, tzinfo=timezone.utc)
        first = {"id": 10, "event": "workflow_run", "created_at": "2026-11-03T07:38:00Z",
                 "status": "completed", "conclusion": "success"}
        def fetch(url, token):
            self.assertIn("event=workflow_run", url)
            return {"workflow_runs": [first, {**first, "id": 11}]}
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now, fetch_json=fetch,
            probe_check=lambda *_: "valid"), "prior_fallback_observed")
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now, fetch_json=fetch,
            probe_check=lambda *_: "no_valid_odds"), "prior_fallback_absent_or_failed")
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now, fetch_json=fetch,
            probe_check=lambda *_: "unavailable"), "fallback_lookup_unavailable")
        first["status"], first["conclusion"] = "in_progress", None
        # PR-origin no-op runs can overlap the serialized operational group;
        # their incomplete state must not suppress an eligible fallback.
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now, fetch_json=fetch), "prior_fallback_absent_or_failed")
        first["status"], first["conclusion"] = "completed", "failure"
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now, fetch_json=fetch), "prior_fallback_absent_or_failed")


    def test_in_progress_noop_does_not_hide_completed_valid_fallback(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T07:45:00Z"}
        now = datetime(2026, 11, 3, 7, 50, tzinfo=timezone.utc)
        pending_noop = {"id": 10, "event": "workflow_run",
                        "created_at": "2026-11-03T07:48:00Z",
                        "status": "in_progress", "conclusion": None}
        completed = {"id": 9, "event": "workflow_run",
                     "created_at": "2026-11-03T07:40:00Z",
                     "status": "completed", "conclusion": "success"}
        checked = []
        def probe(repository, token, run_id):
            checked.append(run_id)
            return "valid"
        result = gate.prior_fallback_guard(
            trigger, "a/b", "token", 11, now=now,
            fetch_json=lambda *_: {"workflow_runs": [pending_noop, completed]},
            probe_check=probe)
        self.assertEqual(result, "prior_fallback_observed")
        self.assertEqual(checked, [9])

    def test_prior_fallback_paginates_busy_history_without_false_absence(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T07:38:00Z"}
        now = datetime(2026, 11, 3, 7, 50, tzinfo=timezone.utc)
        noisy = [{"id": i + 100, "event": "workflow_run",
                  "created_at": "2026-11-03T07:40:00Z",
                  "status": "completed", "conclusion": "failure"} for i in range(100)]
        verified = {"id": 99, "event": "workflow_run",
                    "created_at": "2026-11-03T07:41:00Z",
                    "status": "completed", "conclusion": "success"}
        pages = []
        def fetch(url, token):
            pages.append(url)
            return {"workflow_runs": noisy if "&page=1" in url else [verified]}
        result = gate.prior_fallback_guard(
            trigger, "a/b", "token", 500, now=now,
            fetch_json=fetch, probe_check=lambda *_: "valid")
        self.assertEqual(result, "prior_fallback_observed")
        self.assertEqual(len(pages), 2)

    def test_prior_fallback_fails_closed_if_all_history_pages_are_full(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T07:38:00Z"}
        now = datetime(2026, 11, 3, 7, 50, tzinfo=timezone.utc)
        noisy = [{"id": i + 100, "event": "workflow_run",
                  "created_at": "2026-11-03T07:40:00Z",
                  "status": "completed", "conclusion": "failure"} for i in range(100)]
        urls = []
        def fetch(url, token):
            urls.append(url)
            return {"workflow_runs": noisy}
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 500, now=now, fetch_json=fetch),
            "fallback_lookup_unavailable")
        self.assertEqual(len(urls), 5)

    def test_prior_valid_200_requires_matching_scheduled_upstream_and_slot(self):
        from datetime import datetime, timezone
        import io
        import zipfile
        slot = datetime(2026, 11, 3, 7, 25, tzinfo=timezone.utc)
        run_created = datetime(2026, 11, 3, 7, 41, tzinfo=timezone.utc)
        trigger = {"event": "workflow_run", "upstream_event": "schedule",
                   "upstream_workflow": gate.SECONDARY_UPSTREAM,
                   "upstream_branch": "main", "upstream_run_id": 42,
                   "upstream_created_at": "2026-11-03T07:38:00Z"}
        evidence = {"source_status": "ok", "trigger": trigger,
                    "samples": [{"race_code": "202611030111",
                                 "attempts": [{"http": 200, "state": "valid_200",
                                               "latency_ms": 80}]}]}
        artifacts = lambda *_: {"artifacts": [
            {"name": "live-odds-metrics", "id": 7, "expired": False}]}
        def probe(record):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("live_odds_metrics.json", json.dumps(record))
            return gate.direct_probe_evidence(
                "a/b", "token", 10, fetch_json=artifacts,
                fetch_zip=lambda *_: buffer.getvalue(),
                expected_slot=slot, run_created_at=run_created)
        self.assertEqual(probe(evidence), "valid")
        self.assertEqual(probe({**evidence, "trigger": {**trigger, "upstream_event": "push"}}),
                         "no_valid_odds")
        self.assertEqual(probe({**evidence, "trigger": {**trigger, "upstream_branch": "dev"}}),
                         "no_valid_odds")
        self.assertEqual(probe({**evidence, "trigger": {**trigger, "upstream_run_id": None}}),
                         "no_valid_odds")
        self.assertEqual(probe({**evidence, "trigger": {**trigger,
                          "upstream_created_at": "2026-11-03T05:38:00Z"}}),
                         "no_valid_odds")
        self.assertEqual(probe({**evidence, "trigger": None}), "no_valid_odds")
        self.assertEqual(probe({**evidence, "source_status": "fallback_ineligible"}),
                         "no_valid_odds")

    def test_secondary_fallback_fails_closed_on_missing_history(self):
        from datetime import datetime, timezone
        trigger = {"upstream_created_at": "2026-11-03T07:38:00Z"}
        now = datetime(2026, 11, 3, 7, 40, tzinfo=timezone.utc)
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 12, now=now,
            fetch_json=lambda *_: {"workflow_runs": None}), "fallback_lookup_unavailable")
        self.assertEqual(gate.prior_fallback_guard(
            trigger, "a/b", "token", 12, now=now,
            fetch_json=lambda *_: {"workflow_runs": []}), "prior_fallback_absent_or_failed")


if __name__ == "__main__":
    unittest.main()
