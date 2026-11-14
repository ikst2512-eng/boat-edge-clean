"""Research-only K roster bridge tests: synthetic rows, never official proof."""
import copy
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from scenario_official_K_training_roster_bridge import (
    _training_history, replay_K_and_join_future_exhibition,
    TRAIN_N, FULL_N, TEST_N,
)
from scenario_exhibition_course_head_research import (
    prepare_course_holder_head_study,
)
from test_scenario_exhibition_course_head_research import input_case


def fake_92day_K_rows(holder="4511"):
    days = [date(2026, 8, 1)+timedelta(days=i) for i in range(92)]
    daily = [{
        "day": d.strftime("%Y%m%d"),
        "official_raw_lzh_sha256": "a"*64,
        "decoded_text_sha256": "b"*64,
    } for d in days]
    training_days = days[:61]
    testing_days = days[61:]
    rows = []
    for i in range(FULL_N):
        d = (training_days[i % 61] if i < TRAIN_N
             else testing_days[(i-TRAIN_N) % 31])
        rows.append({
            "day": d.strftime("%Y%m%d"),
            "month": d.strftime("%m"),
            "venue": f"{i % 24+1:02d}",
            "c1_registration": (holder if i % 17 == 0 else str(5000+i % 2000)),
            "c2_registration": str(7000+i % 1000),
            "boat1_registration": str(5000+i % 2000),
            "boat2_registration": str(7000+i % 1000),
            "boat1_actual_course": 1,
            "boat2_actual_course": 2,
            "c1_escape": int(i % 3 != 0),
            "c2_sashi": int(i % 11 == 0),
        })
    return rows, daily


class OriginalKTrainingIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = input_case(2)
        cls.target = cls.case[3]["race_code"]
        cls.holder = next(
            r["registration_id"]
            for r in cls.case[3]["exhibition_features_by_boat"]
            if r["exhibition_course_only"] == 1)
        cls.rows, cls.daily = fake_92day_K_rows(cls.holder)

    def derive(self, rows=None, daily=None, case=None):
        case = case or self.case
        return _training_history(
            self.rows if rows is None else rows,
            self.daily if daily is None else daily,
            case[3]["race_code"], case[3])

    def test_92day_training_only_source_and_same_future_course_holder(self):
        h = self.derive()
        self.assertEqual(h["national_training_race_count"], TRAIN_N)
        self.assertEqual(h["historic_training_end_date_jst"], "2026-09-30")
        self.assertEqual(h["C1_athlete_registration"], self.holder)
        self.assertEqual(
            h["C1_athlete_training_race_count"],
            sum(r["c1_registration"] == self.holder
                for r in self.rows[:TRAIN_N]))
        self.assertEqual(
            h["national_training_C1_escape_count"],
            sum(r["c1_escape"] for r in self.rows[:TRAIN_N]))
        v=h["venue_code"]
        self.assertEqual(h["venue_training_race_count"],
                         sum(r["venue"]==v for r in self.rows[:TRAIN_N]))
        self.assertEqual(h["venue_training_C1_escape_count"],
                         sum(r["c1_escape"] for r in self.rows[:TRAIN_N]
                             if r["venue"] == v))
        self.assertFalse(h["official_source_receipt_independently_authenticated"])
        self.assertFalse(h["exhibition_is_final_race_entry"])
        s = prepare_course_holder_head_study(*self.case[:4], h)
        self.assertEqual(s["history_source_join"]["exhibition_course1_boat"],2)
        self.assertFalse(s["history_counts_applied_to_head_or_world_weights"])
        self.assertFalse(s["original_K_history_replayed_and_verified"])

    def test_october_outcome_change_cannot_leak_into_aug_sep_history(self):
        old = self.derive()
        rows=copy.deepcopy(self.rows)
        for r in rows[TRAIN_N:]:
            r["c1_escape"] = 1-r["c1_escape"]
            r["c2_sashi"] = 1-r["c2_sashi"]
        self.assertEqual(old, self.derive(rows=rows),
                         "October holdout outcomes must never train the target")
        self.assertEqual(len(self.rows)-TRAIN_N, TEST_N)

    def test_frozen_size_dates_and_daily_sha_are_required(self):
        bad_cases = [
            ("missing_eligible", self.rows[:-1], self.daily),
            ("wrong_daily_source_count", self.rows, self.daily[:-1]),
        ]
        for label, rows, daily in bad_cases:
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.derive(rows=rows, daily=daily)
        changed=copy.deepcopy(self.daily)
        changed[0]["official_raw_lzh_sha256"]="bad"
        with self.assertRaisesRegex(ValueError, "K_replay_original_day_SHA"):
            self.derive(daily=changed)
        changed=copy.deepcopy(self.rows)
        changed[0]["day"]="20261114"
        with self.assertRaises(ValueError):
            self.derive(rows=changed)
        changed=copy.deepcopy(self.rows)
        changed[0]["month"]="10"
        with self.assertRaises(ValueError):
            self.derive(rows=changed)

    def test_athlete_and_venue_projections_must_be_exact(self):
        h=self.derive()
        c=list(input_case(4))
        new=self.derive(case=c)
        self.assertNotEqual(
            h["C1_athlete_registration"],new["C1_athlete_registration"])
        self.assertNotEqual(
            h["C1_athlete_training_race_count"],new["C1_athlete_training_race_count"])
        c=list(copy.deepcopy(self.case))
        c[3]["race_code"]="202610311911"
        with self.assertRaisesRegex(ValueError,"K_replay_target_or_full_cohort"):
            self.derive(case=c)
        c=list(copy.deepcopy(self.case))
        c[3]["exhibition_features_by_boat"][1]["registration_id"]="not-a-registration"
        with self.assertRaises(ValueError):
            self.derive(case=c)

    def test_future_source_identity_and_study_cannot_be_forged(self):
        h=self.derive()
        c=list(copy.deepcopy(self.case))
        c[0]["registrations_by_lane"]["1"]="9999"
        with self.assertRaises(ValueError):
            prepare_course_holder_head_study(*c[:4],h)
        h["C1_athlete_registration"]="9999"
        with self.assertRaises(ValueError):
            prepare_course_holder_head_study(*self.case[:4],h)

    def test_wrapper_refuses_missing_local_original_before_model_or_parser(self):
        called=[]
        def forbidden(*args):
            called.append(True)
            raise AssertionError("parser must not be invoked")
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"not-official-k.zip"
            p.write_bytes(b"not-an-original")
            with self.assertRaisesRegex(ValueError,"K_original_zip_or_parser"):
                replay_K_and_join_future_exhibition(
                    p, forbidden, *self.case[:4])
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
