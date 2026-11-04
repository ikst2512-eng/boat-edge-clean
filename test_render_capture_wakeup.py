"""Deterministic offline safety tests for an opt-in independent Render wakeup."""
import io
import json
import unittest
from datetime import datetime, timedelta, timezone

from scripts import render_capture_wakeup as mod

JST = timezone(timedelta(hours=9))


def dt(hour, minute, *, day=5):
    return datetime(2026, 11, day, hour, minute, tzinfo=JST)


def item(event, time, *, status="completed", conclusion="success",
         branch="main", id=42):
    return {
        "id": id, "created_at": time.astimezone(timezone.utc).isoformat(),
        "event": event, "status": status, "conclusion": conclusion,
        "head_branch": branch,
    }


class Response(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()
        return False


def mocked(schedule=None, manual=None):
    requests = []
    def request(req, timeout):
        requests.append((req.get_method(), req.full_url, req.data))
        if req.get_method() == "POST":
            result = Response(b"")
            result.status = 204
            return result
        rows = manual if "event=workflow_dispatch" in req.full_url else schedule
        return Response(json.dumps({"workflow_runs": rows or []}).encode())
    return request, requests


class ExternalWakeupTests(unittest.TestCase):
    def test_target_slot_boundaries_every_15_minutes(self):
        for hour in range(7, 21):
            for minute in (10, 25, 40, 55):
                wanted = minute - 3
                slot = mod.eligible_slot("four_mode", dt(hour, minute))
                self.assertEqual(slot, dt(hour, wanted))
        for hour in range(7, 22):
            for minute in (10, 25, 40, 55):
                slot = mod.eligible_slot("clean", dt(hour, minute))
                self.assertEqual(slot, dt(hour, minute - 6))
        self.assertEqual(mod.eligible_slot("clean", dt(22, 10)), dt(22, 4))
        self.assertEqual(mod.eligible_slot("clean", dt(22, 25)), dt(22, 19))
        self.assertEqual(mod.eligible_slot("clean", dt(22, 30)), dt(22, 28))
        self.assertIsNone(mod.eligible_slot("four_mode", dt(21, 10)))
        self.assertIsNone(mod.eligible_slot("clean", dt(22, 35)))
        self.assertIsNone(mod.eligible_slot("clean", dt(23, 0)))
        self.assertIsNone(mod.eligible_slot("four_mode", dt(7, 8)))
        self.assertIsNone(mod.eligible_slot("clean", dt(7, 8)))

    def test_explicit_five_minute_timing_and_timezone(self):
        self.assertIsNone(mod.eligible_slot("four_mode", dt(7, 12)))
        self.assertIsNone(mod.eligible_slot("clean", dt(7, 13)))
        self.assertIsNone(mod.eligible_slot("clean", dt(22, 33)))
        self.assertEqual(
            mod.eligible_slot("clean", dt(7, 10).astimezone(timezone.utc)),
            dt(7, 4))
        with self.assertRaises(ValueError):
            mod.eligible_slot("clean", dt(7, 10).replace(tzinfo=None))

    def test_no_network_or_credential_outside_slots(self):
        def reject(*args, **kwargs):
            self.fail("No network outside eligible windows")
        data = mod.run(token=None, now=dt(22, 57), request=reject)
        self.assertEqual(data["action"], "outside_recovery_windows_no_network")
        self.assertFalse(data["new_forecast_saved_proven"])
        self.assertFalse(data["on_time_cron_proven"])

    def test_missing_secret_fails_before_network(self):
        with self.assertRaisesRegex(ValueError, "GITHUB_DISPATCH_TOKEN_required"):
            mod.run(token="", now=dt(7, 10),
                    request=lambda *args, **kwargs: self.fail("called network"))

    def test_missing_both_runs_dispatches_both_without_publication_claim(self):
        request, calls = mocked()
        data = mod.run(token="TEST_ONLY", now=dt(7, 10), request=request)
        self.assertEqual([m for m, *_ in calls],
                         ["GET", "GET", "GET", "GET", "POST", "POST"])
        self.assertEqual(
            data["workflows"]["clean"]["action"],
            "dispatch_accepted_not_forecast_proof")
        self.assertEqual(
            data["workflows"]["four_mode"]["action"],
            "dispatch_accepted_not_forecast_proof")
        self.assertEqual([name for method, name, _ in calls if method == "POST"],
                         [
                          "https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/workflows/clean-prospective.yml/dispatches",
                          "https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/workflows/four-mode-prospective-capture.yml/dispatches",
                         ])
        self.assertTrue(all(json.loads(data) == {"ref": "main"}
                            for method, url, data in calls if method == "POST"))
        self.assertFalse(data["new_forecast_saved_proven"])
        self.assertFalse(data["formal"])

    def test_2100_hour_only_clean_is_live(self):
        request, calls = mocked()
        out = mod.run(token="TEST", now=dt(21, 10), request=request)
        self.assertEqual(out["workflows"]["four_mode"]["reason"],
                         "outside_jst_recovery_window")
        self.assertEqual([x[0] for x in calls], ["GET", "GET", "POST"])

    def test_actual_success_and_active_run_prevent_duplicate(self):
        for status, conclusion in (
            ("completed", "success"),
            ("queued", None),
            ("in_progress", None),
            ("completed", None),
        ):
            with self.subTest(status=status, conclusion=conclusion):
                direct = [item("schedule", dt(7, 8),
                               status=status, conclusion=conclusion)]
                request, calls = mocked(schedule=direct)
                data = mod.run(token="TEST", now=dt(7, 10),
                               request=request)
                self.assertEqual(data["workflows"]["four_mode"]["action"],
                                 "no_dispatch")
                self.assertEqual(data["workflows"]["clean"]["action"],
                                 "no_dispatch")
                self.assertEqual(len([x for x in calls if x[0] == "POST"]), 0)

    def test_failed_schedule_allows_recovery_but_no_proof(self):
        request, calls = mocked(schedule=[
            item("schedule", dt(7, 8), conclusion="failure")])
        out = mod.run(token="TEST", now=dt(7, 10), request=request)
        self.assertEqual(out["workflows"]["four_mode"]["action"],
                         "dispatch_accepted_not_forecast_proof")
        self.assertEqual(out["workflows"]["clean"]["action"],
                         "dispatch_accepted_not_forecast_proof")
        self.assertEqual(sum(1 for method, *_ in calls if method == "POST"), 2)

    def test_prior_manual_in_slot_suppresses_retry(self):
        manual = [item("workflow_dispatch", dt(7, 8),
                       conclusion="failure")]
        request, calls = mocked(manual=manual)
        out = mod.run(token="TEST", now=dt(7, 10), request=request)
        self.assertTrue(all(x["reason"] == "previous_dispatch_or_active_job"
                            for x in out["workflows"].values()))
        self.assertFalse(any(m == "POST" for m, *_ in calls))

    def test_previous_slot_success_does_not_block_new_slot(self):
        schedule = [item("schedule", dt(7, 8))]
        manual = [item("workflow_dispatch", dt(7, 9))]
        request, calls = mocked(schedule=schedule, manual=manual)
        out = mod.run(token="TEST", now=dt(7, 25), request=request)
        self.assertEqual([out["workflows"][k]["action"]
                          for k in mod.WORKFLOWS],
                         ["dispatch_accepted_not_forecast_proof"] * 2)
        self.assertEqual(sum(m == "POST" for m, *_ in calls), 2)

    def test_older_queued_job_prevents_duplicate(self):
        direct = [item("schedule", dt(7, 8),
                       status="queued", conclusion=None)]
        request, calls = mocked(schedule=direct)
        out = mod.run(token="TEST", now=dt(7, 25), request=request)
        self.assertEqual(out["workflows"]["four_mode"]["reason"],
                         "previous_dispatch_or_active_job")
        self.assertFalse(any(m == "POST" for m, *_ in calls))

    def test_explicit_nonmain_run_not_false_main_success(self):
        manual = [item("workflow_dispatch", dt(7, 8),
                       branch="research/branch")]
        request, calls = mocked(manual=manual)
        out = mod.run(token="TEST", now=dt(7, 10), request=request)
        self.assertEqual(sum(m == "POST" for m, *_ in calls), 2)
        self.assertEqual(out["workflows"]["clean"]["action"],
                         "dispatch_accepted_not_forecast_proof")

    def test_malformed_unknown_history_fails_closed_without_dispatch(self):
        for corrupt in (
            {"event": "schedule", "id": 5, "status": "completed",
             "created_at": dt(7, 8).isoformat()},
            {"event": "schedule", "id": "5", "status": "completed",
             "created_at": dt(7, 8).isoformat(), "head_branch": "main"},
        ):
            with self.subTest(corrupt=corrupt):
                request, calls = mocked(schedule=[corrupt])
                with self.assertRaises(ValueError):
                    mod.run(token="TEST", now=dt(7, 10), request=request)
                self.assertFalse(any(m == "POST" for m, *_ in calls))

    def test_first_page_truncated_does_not_dispatch(self):
        records = [item("schedule", dt(7, 8), id=i+1)
                   for i in range(100)]
        request, calls = mocked(schedule=records)
        with self.assertRaisesRegex(ValueError, "pagination_incomplete"):
            mod.run(token="TEST", now=dt(7, 10), request=request)
        self.assertFalse(any(m == "POST" for m, *_ in calls))

    def test_second_history_error_prevents_any_partial_dispatch(self):
        calls = []
        def request(req, timeout):
            calls.append((req.get_method(), req.full_url))
            if req.get_method() == "POST":
                self.fail("first dispatch must not happen before second workflow check")
            if ("four-mode-prospective-capture.yml" in req.full_url
                    and "event=schedule" in req.full_url):
                return Response(b'{"message":"history temporarily unavailable"}')
            return Response(b'{"workflow_runs":[]}')
        with self.assertRaisesRegex(ValueError, "github_history_missing_or_malformed"):
            mod.run(token="TEST", now=dt(7, 10), request=request)
        self.assertEqual([m for m, _ in calls], ["GET", "GET", "GET"])

    def test_refused_dispatch_fails_job(self):
        def request(req, timeout):
            if req.get_method() == "POST":
                return Response(b"")
            return Response(b'{"workflow_runs":[]}')
        with self.assertRaisesRegex(RuntimeError, "dispatch_not_accepted"):
            mod.run(token="TEST", now=dt(7, 10), request=request)

    def test_external_slot_contract_matches_both_real_github_crons(self):
        # Do not allow the optional Render wakeup's hardcoded slot table to
        # silently drift from the actual, separately maintained Actions cron.
        # This is read-only: it never creates a cron service or dispatches.
        import re
        from pathlib import Path

        def expand(expr):
            values = set()
            for item in expr.split(","):
                if "-" in item:
                    start, end = (int(p) for p in item.split("-", 1))
                    self.assertLessEqual(start, end)
                    values.update(range(start, end + 1))
                else:
                    values.add(int(item))
            return values

        for kind, workflow in (
            ("clean", ".github/workflows/clean-prospective.yml"),
            ("four_mode", ".github/workflows/four-mode-prospective-capture.yml"),
        ):
            with self.subTest(kind=kind):
                yaml = Path(workflow).read_text(encoding="utf-8")
                declarations = re.findall(
                    r"(?m)^\s+- cron: '([^']+)'", yaml)
                self.assertTrue(declarations, "source cron missing")
                actual = set()
                for expression in declarations:
                    fields = expression.split()
                    self.assertEqual(len(fields), 5)
                    # Day-specific schedules require an explicit contract
                    # update, not an accidental partial match.
                    self.assertEqual(fields[2:], ["*", "*", "*"])
                    for hour in expand(fields[1]):
                        for minute in expand(fields[0]):
                            self.assertTrue(0 <= hour < 24)
                            self.assertTrue(0 <= minute < 60)
                            actual.add(((hour + 9) % 24, minute))
                slots = mod.planned_slots(kind, dt(12, 0))
                expected = {(slot.hour, slot.minute) for slot in slots}
                self.assertEqual(actual, expected,
                                 "Render wakeup slots drifted from GitHub cron")

                # The documented single Render UTC */5 cron must offer a
                # tick in the script's narrow eligible window for EVERY
                # primary slot, including CLEAN's final 22:28 JST.
                for slot in slots:
                    ticks = []
                    for minutes_after in range(1, 9):
                        t = slot + timedelta(minutes=minutes_after)
                        utc_hour = t.astimezone(timezone.utc).hour
                        if (t.minute % 5 == 0 and
                                (utc_hour >= 22 or utc_hour <= 13) and
                                mod.eligible_slot(kind, t) == slot):
                            ticks.append(t)
                    self.assertTrue(
                        ticks,
                        f"No */5 UTC 22-13 Render recovery tick for {kind} {slot.isoformat()}"
                    )

    def test_workflow_ci_includes_render_safety_suite(self):
        from pathlib import Path
        wf = Path(".github/workflows/four-mode-capture-watchdog.yml").read_text()
        self.assertIn("test_render_capture_wakeup", wf)
        self.assertIn("scripts/render_capture_wakeup.py", wf)
        self.assertEqual(wf.count("- cron:"), 4)
        self.assertIn("run: python -m scripts.clean_prospective_watchdog", wf)


if __name__ == "__main__":
    unittest.main()
