"""Security regressions: nonmonotone GitHub server Date is not publication proof.

Mocks only; no actual future candidate is created or observed by these tests.
"""
from datetime import datetime, timezone
from email.utils import format_datetime
import unittest

from position_sensitive_manual_publisher import (
    API, PROPOSED_LEDGER_BRANCH, manual_publish_one,
)
from test_position_sensitive_manual_publisher import (
    CODE, MockGitHub, valid_clock,
)


def server_date(jst):
    return format_datetime(
        datetime.fromisoformat(jst).astimezone(timezone.utc), usegmt=True)


class RetimedAPI:
    """Wrap the existing synthetic GitHub fixture; rewrite only Date."""
    def __init__(self, date_for, original=None):
        self.api = original or MockGitHub()
        self.date_for = date_for

    def __call__(self, method, url, data):
        status, headers, body = self.api(method, url, data)
        candidate = f"/contents/position_sensitive_research/{CODE}.json"
        stage = None
        if method == "GET" and url.endswith(
                candidate + "?ref=" + PROPOSED_LEDGER_BRANCH):
            stage = "not_found"
        elif method == "PUT" and url.endswith(candidate):
            stage = "created"
        elif method == "GET" and url.endswith(candidate+"?ref="+"c"*40):
            stage = "readback"
        when = self.date_for.get(stage)
        if when is not None:
            headers = {**headers, "Date": server_date(when)}
        return status, headers, body


class ManualServerChronologySafetyTests(unittest.TestCase):
    def test_missing_404_cannot_predate_locally_frozen_candidate(self):
        clock = RetimedAPI({"not_found": "2026-11-09T10:05:09+09:00"})
        with self.assertRaisesRegex(
                ValueError, "candidate_absence_server_clock_regressed"):
            manual_publish_one(CODE, clock, valid_clock())
        self.assertFalse(any(op == "PUT" for op, _ in clock.api.calls))

    def test_201_server_date_before_404_cannot_certify_creation(self):
        clock = RetimedAPI({"created": "2026-11-09T10:05:29+09:00"})
        with self.assertRaisesRegex(
                ValueError, "github_create_response_clock_not_after_absence"):
            manual_publish_one(CODE, clock, valid_clock())
        self.assertIsNotNone(clock.api.created_bytes)

    def test_201_same_second_as_absence_is_ambiguous(self):
        clock = RetimedAPI({"created": "2026-11-09T10:05:30+09:00"})
        with self.assertRaisesRegex(
                ValueError, "github_create_response_clock_not_after_absence"):
            manual_publish_one(CODE, clock, valid_clock())

    def test_200_readback_equal_to_201_second_is_ambiguous(self):
        clock = RetimedAPI({"readback": "2026-11-09T10:05:40+09:00"})
        with self.assertRaisesRegex(
                ValueError, "github_remote_candidate_not_early_or_byte_mismatch"):
            manual_publish_one(CODE, clock, valid_clock())

    def test_strict_404_201_readback_sequence_accepted_but_not_formal(self):
        clock = RetimedAPI({})
        result = manual_publish_one(CODE, clock, valid_clock())
        self.assertEqual(result["status"],
                         "manual_create_and_remote_observation_preT12_nonformal")
        self.assertFalse(result["candidate_first_remote_receipt_independently_verified"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["model_improvement_proven"])
        self.assertFalse(result["promotion_allowed"])

    def test_remote_404_date_after_cutoff_still_rejected(self):
        clock = RetimedAPI({"not_found": "2026-11-09T12:28:00+09:00"})
        with self.assertRaisesRegex(ValueError, "candidate_absence_checked_too_late"):
            manual_publish_one(CODE, clock, valid_clock())
        self.assertFalse(any(op == "PUT" for op, _ in clock.api.calls))


if __name__ == "__main__":
    unittest.main()
