"""Synthetic GitHub API metadata trend fixtures, not original source witnesses."""
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from urllib.error import HTTPError

from scripts.audit_t12_multiday_schedule_trend import trend

REPO = "ikst2512-eng/boat-edge-clean"
NOW = datetime.fromisoformat("2026-11-08T13:10:00+00:00")
COUNTS = {
    "20261101": (2, 1),
    "20261102": (1, 1),
    "20261103": (1, 1),
    "20261104": (1, 1),
    "20261105": (1, 1),
    "20261106": (1, 1),
    "20261107": (2, 1),
    "20261108": (2, 0),
}


def day_fixture(day, inside, outside):
    runs = []
    for n in range(inside):
        runs.append({
            "run_id": int(day)*100+n,
            "created_at_utc": f"{day[:4]}-{day[4:6]}-{day[6:8]}T05:{n:02d}:00+00:00",
            "created_within_declared_cron_hours": True,
            "conclusion": "failure" if day == "20261107" and n == 0 else "success"
        })
    for n in range(outside):
        runs.append({
            "run_id": int(day)*100+20+n,
            "created_at_utc": f"{day[:4]}-{day[4:6]}-{day[6:8]}T13:{n:02d}:00+00:00",
            "created_within_declared_cron_hours": False,
            "conclusion": "success",
        })
    return {
        "schema": "OFFICIAL_PAIR_SCHEDULE_CONTINUITY_AUDIT_V1",
        "utc_day": day,
        "as_of_utc": NOW.isoformat(),
        "workflow_path": ".github/workflows/research-live-preview-evidence.yml",
        "expected_cron_assumption": "*/5 0-12 * * *",
        "expected_slots_full_day": 156,
        "elapsed_nominal_slots_at_snapshot": 156,
        "future_nominal_slots": 0,
        "observed_official_pair_schedule_runs": inside+outside,
        "observed_within_declared_cron_hours": inside,
        "observed_outside_declared_cron_hours": outside,
        "schedule_slot_identity_verified": False,
        "missing_trigger_root_cause_verified": False,
        "raw_official_source_receipts_verified": False,
        "full_t12_source_certified": False,
        "run_success": sum(r["conclusion"]=="success" for r in runs),
        "run_failure": sum(r["conclusion"]=="failure" for r in runs),
        "run_other_or_incomplete": 0,
        "runs": runs,
    }


def fixtures():
    return {day: day_fixture(day,*values) for day,values in COUNTS.items()}


def fake(rows):
    def load(repo, day, token, *, as_of=None):
        if repo != REPO or token != "test-token":
            raise AssertionError("foreign repository or token")
        if as_of != NOW:
            raise AssertionError("inconsistent snapshot")
        return deepcopy(rows[day])
    return load


class MultiDayAudit(unittest.TestCase):
    def inspect(self, rows=None):
        return trend(REPO,"20261101","20261108","test-token",
                     daily=fake(fixtures() if rows is None else rows),
                     as_of=NOW)

    def test_full_eight_day_historical_counts_not_http_failures(self):
        r=self.inspect()
        self.assertEqual(r["configured_nominal_slots"],1248)
        self.assertEqual(r["observed_schedule_run_creations"],18)
        self.assertEqual(r["created_in_declared_cron_hours"],11)
        self.assertEqual(r["created_outside_declared_cron_hours"],7)
        self.assertEqual(r["nominal_invocation_count_shortfall"],1230)
        self.assertEqual(r["run_creation_to_nominal_slot_pct"],1.44)
        self.assertEqual(len(r["days"]),8)
        self.assertEqual(r["run_failure"],1)
        self.assertFalse(r["absent_run_http_errors_proved"])
        self.assertFalse(r["actual_slot_identity_verified"])
        self.assertFalse(r["missing_trigger_root_cause_verified"])
        self.assertFalse(r["official_source_originals_replayed"])
        self.assertFalse(r["formal"])
        self.assertFalse(r["accuracy_scoring_allowed"])
        self.assertIsNone(r["formal_accuracy_denominator"])

    def test_last_day_has_two_not_one_invocations(self):
        r=self.inspect()
        d=r["days"][-1]
        self.assertEqual(d["day_utc_jst"],"20261108")
        self.assertEqual(d["observed_schedule_run_creations"],2)
        self.assertEqual(d["created_outside_declared_hours"],0)
        self.assertEqual(d["observation_rate_pct"],1.28)

    def test_reject_early_snapshot_as_completed_day(self):
        with self.assertRaisesRegex(ValueError,"slot not yet elapsed"):
            self.inspect_clock(datetime.fromisoformat("2026-11-08T12:54:59+00:00"))

    def inspect_clock(self,now):
        return trend(REPO,"20261101","20261108","test-token",
                     daily=fake(fixtures()),as_of=now)

    def test_unsupported_range_and_bad_days(self):
        for start,end in (("20261109","20261108"),("20261001","20261108"),
                          ("20261101","20261302"),("2026110x","20261108")):
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):
                trend(REPO,start,end,"test-token",daily=fake(fixtures()),as_of=NOW)

    def test_reject_cross_day_forgery(self):
        rows=fixtures();rows["20261106"]["utc_day"]="20261105"
        with self.assertRaisesRegex(ValueError,"cross-day"):
            self.inspect(rows)

    def test_reject_unsupported_cron_assumption_and_claimed_proof(self):
        for k,v in (
            ("expected_cron_assumption","0 9 * * *"),
            ("schedule_slot_identity_verified",True),
            ("missing_trigger_root_cause_verified",True),
            ("raw_official_source_receipts_verified",True),
            ("full_t12_source_certified",True),
        ):
            with self.subTest(key=k):
                rows=fixtures();rows["20261105"][k]=v
                with self.assertRaises(ValueError):
                    self.inspect(rows)

    def test_reject_miscounted_or_duplicate_events(self):
        for k,v in (("observed_official_pair_schedule_runs",3),
                    ("observed_within_declared_cron_hours",0),
                    ("run_success",100),
                    ("elapsed_nominal_slots_at_snapshot",155),
                    ("future_nominal_slots",1)):
            with self.subTest(k=k):
                rows=fixtures();rows["20261106"][k]=v
                with self.assertRaises(ValueError):
                    self.inspect(rows)
        rows=fixtures()
        rows["20261106"]["runs"][0]["run_id"]=rows["20261105"]["runs"][0]["run_id"]
        with self.assertRaisesRegex(ValueError,"duplicate"):
            self.inspect(rows)

    def test_outside_cron_hours_cannot_be_disguised_as_inside(self):
        rows=fixtures();rows["20261105"]["runs"][-1]["created_within_declared_cron_hours"]=True
        with self.assertRaisesRegex(ValueError,"classification"):
            self.inspect(rows)

    def test_403_propagates(self):
        def denied(*args,**kwargs):
            raise HTTPError("https://api.github.com/",403,"Forbidden",{},None)
        with self.assertRaises(HTTPError):
            trend(REPO,"20261108","20261108","test-token",
                  daily=denied,as_of=NOW)

    def test_missing_token_and_unverified_now_rejected(self):
        with self.assertRaisesRegex(ValueError,"token"):
            trend(REPO,"20261108","20261108",None,
                  daily=fake(fixtures()),as_of=NOW)
        with self.assertRaisesRegex(ValueError,"UTC"):
            trend(REPO,"20261108","20261108","test-token",
                  daily=fake(fixtures()),
                  as_of=datetime(2026,11,8,13,10))

    def test_formal_claims_never_from_metadata(self):
        r=self.inspect()
        self.assertEqual([d["day_utc_jst"] for d in r["days"]],sorted(COUNTS))
        self.assertEqual(r["run_success"],17)
        self.assertEqual(r["run_other_or_incomplete"],0)
        self.assertEqual(sum(x["nominal_configured_slots"] for x in r["days"]),1248)
        self.assertFalse(r["t12_eligible"])


if __name__=="__main__":
    unittest.main()
