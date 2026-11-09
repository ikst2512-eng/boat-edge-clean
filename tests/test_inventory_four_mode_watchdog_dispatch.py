import unittest
from datetime import datetime, timezone
from scripts.inventory_four_mode_watchdog_dispatch import inventory

NOW = datetime(2026, 11, 3, 6, tzinfo=timezone.utc)

def row(id, event, at, conclusion="success", *, branch="main",
        head_repo="example/project"):
    return {"id": id, "event": event, "created_at": at,
            "status": "completed", "conclusion": conclusion,
            "head_branch": branch,
            "head_repository": ({"full_name": head_repo} if head_repo else None),
            "html_url": f"https://github.com/example/project/actions/runs/{id}"}

class WatchdogInventoryTest(unittest.TestCase):
    def test_split_schedule_dispatch_and_watchdog(self):
        events = {
            ("four-mode-prospective-capture.yml", "schedule"): [row(1, "schedule", "2026-11-03T03:54:14Z")],
            ("four-mode-prospective-capture.yml", "workflow_dispatch"): [row(2, "workflow_dispatch", "2026-11-03T05:30:00Z")],
            ("four-mode-capture-watchdog.yml", "schedule"): [],
            ("four-mode-capture-watchdog.yml", "push"): [row(3, "push", "2026-11-03T05:25:00Z")],
            ("four-mode-capture-watchdog.yml", "workflow_run"): [],
            ("clean-prospective.yml", "workflow_dispatch"): []}
        def fetch(url, token):
            for (workflow, event), vals in events.items():
                if workflow in url and ("event=" + event) in url:
                    return {"workflow_runs": vals}
            raise AssertionError(url)
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(d["capture_schedule"]["returned"], 1)
        self.assertEqual(d["capture_workflow_dispatch"]["success"], 1)
        self.assertEqual(d["watchdog_push"]["returned"], 1)
        self.assertEqual(d["minutes_since_latest_capture"], 30)
        self.assertEqual(d["latest_capture"]["id"], 2)
        self.assertFalse(d["dispatch_accepted_proven"])
        self.assertFalse(d["forecast_saved_proven"])

    def test_full_capture_history_is_kept_for_daily_liveness(self):
        calls = [row(i, "schedule", "2026-11-03T00:07:00Z")
                 for i in range(1, 31)]
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                return {"workflow_runs": calls}
            return {"workflow_runs": []}
        result = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(len(result["recent_capture_runs"]), 30)
        self.assertEqual(result["recent_capture_runs"][-1]["id"], 30)

    def test_feature_branch_success_cannot_mask_missing_main_capture(self):
        # On a feature branch the workflow test job can pass while capture is
        # skipped. A green workflow_dispatch is not main publication evidence.
        def fetch(url, token):
            if ("four-mode-prospective-capture.yml" in url
                    and "event=workflow_dispatch" in url):
                return {"workflow_runs": [
                    row(901, "workflow_dispatch", "2026-11-03T05:30:00Z",
                        branch="audit/feature-only")]}
            return {"workflow_runs": []}
        result = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(result["capture_workflow_dispatch"]["returned"], 0)
        self.assertEqual(result["capture_workflow_dispatch"]["success"], 0)
        self.assertIsNone(result["latest_capture"])
        scope = result["source_coverage"][
            "four-mode-prospective-capture.yml:workflow_dispatch"]
        self.assertEqual(scope["returned"], 1)
        self.assertEqual(scope["main_verified_returned"], 0)
        self.assertEqual(scope["excluded_nonmain_or_unverified_run_ids"], [901])
        from scripts.audit_four_mode_daily_capture_liveness import report
        self.assertEqual(report("20261103", result)["status"],
                         "no_capture_runs_observed")

    def test_missing_or_foreign_head_repo_fails_closed(self):
        for owner in (None, "elsewhere/fork"):
            with self.subTest(owner=owner):
                def fetch(url, token):
                    if ("four-mode-prospective-capture.yml" in url
                            and "event=workflow_dispatch" in url):
                        return {"workflow_runs": [
                            row(902, "workflow_dispatch", "2026-11-03T05:30:00Z",
                                head_repo=owner)]}
                    return {"workflow_runs": []}
                result = inventory("example/project", "fake", fetch, NOW)
                self.assertEqual(result["capture_workflow_dispatch"]["success"], 0)
                self.assertEqual(result["source_coverage"][
                    "four-mode-prospective-capture.yml:workflow_dispatch"
                ]["excluded_nonmain_or_unverified_run_ids"], [902])
                self.assertFalse(result["forecast_saved_proven"])

    def test_schedule_with_unknown_branch_cannot_claim_main_liveness(self):
        def fetch(url, token):
            if ("four-mode-prospective-capture.yml" in url
                    and "event=schedule" in url):
                return {"workflow_runs": [
                    row(903, "schedule", "2026-11-03T02:00:00Z", branch=None)]}
            return {"workflow_runs": []}
        result = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(result["capture_schedule"]["success"], 0)
        self.assertEqual(result["source_coverage"][
            "four-mode-prospective-capture.yml:schedule"
        ]["excluded_nonmain_or_unverified_run_ids"], [903])

    def test_webhook_watchdog_is_distinct_from_direct_decision_artifacts(self):
        events = {
            ("four-mode-capture-watchdog.yml", "schedule"): [
                row(801, "schedule", "2026-11-03T05:40:00Z")],
            ("four-mode-capture-watchdog.yml", "workflow_run"): [
                row(802, "workflow_run", "2026-11-03T05:50:00Z",
                    "skipped"),
                row(803, "workflow_run", "2026-11-03T05:55:00Z")],
        }
        def fetch(url, token):
            for (workflow, event), data in events.items():
                if workflow in url and ("event=" + event) in url:
                    return {"workflow_runs": data, "total_count": len(data)}
            return {"workflow_runs": [], "total_count": 0}
        result = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(result["watchdog_schedule"]["success"], 1)
        self.assertEqual(result["watchdog_workflow_run"]["returned"], 2)
        self.assertEqual(result["watchdog_workflow_run"]["success"], 1)
        self.assertEqual(result["watchdog_workflow_run"]["skipped"], 1)
        self.assertEqual(result["watchdog_workflow_run"][
            "completed_other_non_success"], 1)
        # Historical artifact audit must not be crowded out by webhook jobs.
        self.assertEqual([r["id"] for r in result["recent_watchdog_runs"]],
                         [801])
        self.assertEqual([r["id"] for r in result["recent_watchdog_workflow_run"]],
                         [803, 802])
        self.assertEqual(result["latest_watchdog"]["id"], 801)
        self.assertEqual(result["latest_watchdog_workflow_run"]["id"], 803)
        self.assertFalse(result["dispatch_accepted_proven"])
        self.assertFalse(result["forecast_saved_proven"])

    def test_webhook_first_page_truncation_not_assumed_complete(self):
        def fetch(url, token):
            if ("four-mode-capture-watchdog.yml" in url
                    and "event=workflow_run" in url):
                return {"workflow_runs": [
                    row(804, "workflow_run", "2026-11-03T05:52:00Z",
                        "skipped")], "total_count": 950}
            return {"workflow_runs": [], "total_count": 0}
        result = inventory("example/project", "fake", fetch, NOW)
        count = result["watchdog_workflow_run"]
        self.assertEqual(count["returned"], 1)
        self.assertEqual(count["skipped"], 1)
        self.assertEqual(count["success"], 0)
        scope = result["source_coverage"][
            "four-mode-capture-watchdog.yml:workflow_run"]
        self.assertTrue(scope["first_page_only"])
        self.assertTrue(scope["may_be_truncated"])
        self.assertEqual(scope["total_count_reported"], 950)

    def test_untrusted_webhook_origin_excluded_from_main_liveness(self):
        def fetch(url, token):
            if ("four-mode-capture-watchdog.yml" in url
                    and "event=workflow_run" in url):
                return {"workflow_runs": [
                    row(805, "workflow_run", "2026-11-03T05:52:00Z",
                        head_repo="foreign/fork")]}
            return {"workflow_runs": []}
        result = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(result["watchdog_workflow_run"]["returned"], 0)
        scope = result["source_coverage"][
            "four-mode-capture-watchdog.yml:workflow_run"]
        self.assertEqual(scope["excluded_nonmain_or_unverified_run_ids"], [805])

    def test_clean_dispatch_and_successful_webhook_samples_separate(self):
        def fetch(url, token):
            if "four-mode-capture-watchdog.yml" in url and "event=workflow_run" in url:
                return {"workflow_runs": [
                    row(904, "workflow_run", "2026-11-03T05:54:00Z", "skipped"),
                    row(905, "workflow_run", "2026-11-03T05:50:00Z")]}
            if "clean-prospective.yml" in url and "event=workflow_dispatch" in url:
                return {"workflow_runs": [
                    row(906, "workflow_dispatch", "2026-11-03T05:50:05Z")]}
            return {"workflow_runs": []}
        data = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(data["clean_workflow_dispatch"]["success"], 1)
        self.assertEqual([r["id"] for r in data["recent_clean_dispatch_runs"]], [906])
        self.assertEqual([r["id"] for r in data["recent_successful_watchdog_workflow_run"]], [905])
        self.assertEqual([r["id"] for r in data["recent_watchdog_workflow_run"]], [904, 905])
        self.assertEqual(data["capture_workflow_dispatch"]["success"], 0)
        self.assertFalse(data["forecast_saved_proven"])

    def test_clean_foreign_branch_is_not_published_main_dispatch(self):
        def fetch(url, token):
            if "clean-prospective.yml" in url and "event=workflow_dispatch" in url:
                return {"workflow_runs": [
                    row(908, "workflow_dispatch", "2026-11-03T05:50:05Z",
                        branch="audit/not-main")]}
            return {"workflow_runs": []}
        data = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(data["clean_workflow_dispatch"]["returned"], 0)
        self.assertEqual(data["source_coverage"][
            "clean-prospective.yml:workflow_dispatch"
        ]["excluded_nonmain_or_unverified_run_ids"], [908])

    def test_no_capture_is_unknown_not_zero_minutes(self):
        def fetch(url, token):
            return {"workflow_runs": []}
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertIsNone(d["minutes_since_latest_capture"])
        self.assertIsNone(d["latest_capture"])

    def test_fail_closed_on_wrong_event_and_malformed_payload(self):
        def wrong(url, token):
            return {"workflow_runs": [row(1, "pull_request", "2026-11-03T01:00:00Z")]}
        with self.assertRaises(ValueError):
            inventory("example/project", "fake", wrong, NOW)
        with self.assertRaises(ValueError):
            inventory("example/project", "fake", lambda *_: {}, NOW)

    def test_reject_missing_token(self):
        with self.assertRaises(ValueError):
            inventory("example/project", "", lambda *_: {"workflow_runs": []}, NOW)

    def test_pending_not_mistaken_for_success(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                r = row(4, "schedule", "2026-11-03T05:58:00Z", None)
                r["status"] = "in_progress"
                return {"workflow_runs": [r]}
            return {"workflow_runs": []}
        d = inventory("example/project", "fake", fetch, NOW)
        self.assertEqual(d["capture_schedule"]["pending"], 1)
        self.assertEqual(d["capture_schedule"]["success"], 0)


    def test_duplicate_ids_on_single_api_page_fail_closed(self):
        def fetch(url, token):
            if "event=schedule" in url and "four-mode-prospective-capture.yml" in url:
                return {"workflow_runs": [row(101, "schedule", "2026-11-03T02:00:00Z"),
                                          row(101, "schedule", "2026-11-03T02:00:00Z")]}
            return {"workflow_runs": []}
        with self.assertRaisesRegex(ValueError, "duplicate workflow run"):
            inventory("example/project", "fake", fetch, NOW)

    def test_duplicate_ids_across_event_pages_fail_closed(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url:
                if "event=schedule" in url:
                    return {"workflow_runs": [row(102, "schedule", "2026-11-03T02:00:00Z")]}
                if "event=workflow_dispatch" in url:
                    return {"workflow_runs": [
                        row(102, "workflow_dispatch", "2026-11-03T03:00:00Z")]}
            return {"workflow_runs": []}
        with self.assertRaisesRegex(ValueError, "same_run_id_in_multiple"):
            inventory("example/project", "fake", fetch, NOW)

    def test_noncompleted_run_claiming_success_is_not_accepted(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                bad = row(103, "schedule", "2026-11-03T03:00:00Z")
                bad["status"] = "in_progress"
                return {"workflow_runs": [bad]}
            return {"workflow_runs": []}
        with self.assertRaisesRegex(ValueError, "noncompleted_run_has_conclusion"):
            inventory("example/project", "fake", fetch, NOW)

    def test_completed_unknown_and_cancelled_are_separate_from_failure(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                return {"workflow_runs": [
                    row(104, "schedule", "2026-11-03T02:00:00Z", None),
                    row(105, "schedule", "2026-11-03T03:00:00Z", "cancelled"),
                    row(106, "schedule", "2026-11-03T04:00:00Z", "failure")]}
            return {"workflow_runs": []}
        result = inventory("example/project", "fake", fetch, NOW)
        counted = result["capture_schedule"]
        self.assertEqual(counted["returned"], 3)
        self.assertEqual(counted["success"], 0)
        self.assertEqual(counted["failed"], 1)
        self.assertEqual(counted["completed_unknown_outcome"], 1)
        self.assertEqual(counted["completed_other_non_success"], 1)
        self.assertEqual(counted["pending"], 0)
        self.assertFalse(result["forecast_saved_proven"])

    def test_incomplete_paginated_listing_not_misreported_complete(self):
        def fetch(url, token):
            if "four-mode-prospective-capture.yml" in url and "event=schedule" in url:
                return {"workflow_runs": [row(107, "schedule", "2026-11-03T02:00:00Z")],
                        "total_count": 4}
            return {"workflow_runs": [], "total_count": 0}
        result = inventory("example/project", "fake", fetch, NOW)
        coverage = result["source_coverage"]["four-mode-prospective-capture.yml:schedule"]
        self.assertEqual(coverage["returned"], 1)
        self.assertEqual(coverage["total_count_reported"], 4)
        self.assertTrue(coverage["may_be_truncated"])

    def test_inconsistent_total_count_and_oversized_page_fail_closed(self):
        payloads = [
            {"workflow_runs": [row(108, "schedule", "2026-11-03T02:00:00Z")],
             "total_count": 0},
            {"workflow_runs": [], "total_count": True},
            {"workflow_runs": [
                row(200+i, "schedule", "2026-11-03T02:00:00Z")
                for i in range(101)]},
        ]
        for payload in payloads:
            with self.subTest(payload_size=len(payload["workflow_runs"])):
                def fetch(url, token):
                    if ("four-mode-prospective-capture.yml" in url
                            and "event=schedule" in url):
                        return payload
                    return {"workflow_runs": []}
                with self.assertRaises(ValueError):
                    inventory("example/project", "fake", fetch, NOW)

if __name__ == "__main__":
    unittest.main()
