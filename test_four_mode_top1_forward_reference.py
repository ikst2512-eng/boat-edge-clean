"""Tests for independent Nov9+ Top1 cohorts; no real result is asserted."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from test_four_mode_all_mode_same_job_shadow import (
    make_original, fixture, capture, JST,
)
from four_mode_top1_forward_reference import compare, START, END, policy


def frozen(root, day):
    raw = make_original()
    original_day = "2026-11-07"
    iso_day = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    raw["race_code"] = day + "0101"
    for key in ("source_title_received_jst", "source_cards_received_jst",
                "generated_at_jst", "deadline_jst"):
        raw[key] = raw[key].replace(original_day, iso_day)
    p, o, git = fixture(root, raw)
    observed = datetime.fromisoformat(iso_day + "T08:09:00+09:00")
    obs = json.loads(o.read_text())
    obs["records"][0]["github_api_server_date_utc"] = (
        observed.astimezone(timezone.utc).isoformat()
    )
    o.write_text(json.dumps(obs), encoding="utf-8")
    now = datetime.fromisoformat(iso_day + "T08:10:00+09:00")
    doc = capture(
        root, p, o, now=now, git=git, clock=lambda: now+timedelta(seconds=1)
    )
    assert doc["frozen_count"] == 1
    return doc


def result(root, code, winning, *, confirmed_at=None):
    day = code[:8]
    iso_day = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    p = root/"confirmed_results"/(code+".json")
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({
        "race_code": code,
        "status": "confirmed",
        "finish_order": [int(x) for x in winning.split("-")],
        "confirmed_at_jst": confirmed_at or iso_day+"T08:45:00+09:00",
        "collected_at_jst": iso_day+"T08:46:00+09:00",
        "source_sha256": "f"*64,
        "source_url": ("https://boatracecsv.github.io/data/results/realtime/"
                       +day[:4]+"/"+day[4:6]+"/"+day[6:8]+".csv"),
    }),encoding="utf-8")


class Top1ForwardReferenceTests(unittest.TestCase):
    def test_policy_exact_future_day_and_zero_formal(self):
        p = policy()
        self.assertEqual(p["eligible_deadline_start_jst"], START)
        self.assertEqual(p["eligible_deadline_end_jst"], END)
        self.assertFalse(p["promotion_allowed"])

    def test_empty_captures_never_become_formal_or_600(self):
        with tempfile.TemporaryDirectory() as d:
            r = compare([], Path(d))
            self.assertEqual(r["reference_slots_reserved_first_600"], 0)
            self.assertEqual(r["top1_by_phase"]["pilot"]["hit"]["denominator"], 0)
            self.assertFalse(r["complete_capture_run_inventory_verified"])
            self.assertFalse(r["model_improvement_proven"])

    def test_nov7_original_retrospective_excluded_even_if_result_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            doc=frozen(root,"20261107")
            code=doc["records"][0]["race_code"]
            result(root,code,doc["records"][0]["baseline"]["hit"][0])
            r=compare([doc],root)
            self.assertEqual(r["reference_slots_reserved_first_600"],0)
            self.assertEqual(r["confirmed_result_matches"],{})

    def test_nov8_registration_day_excluded_even_if_outcome_saved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            doc=frozen(root,"20261108")
            code=doc["records"][0]["race_code"]
            result(root,code,doc["records"][0]["baseline"]["hit"][0])
            r=compare([doc],root)
            self.assertEqual(r["reference_slots_reserved_first_600"],0)

    def test_nov9_missing_result_retains_pilot_slot_not_miss(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);doc=frozen(root,"20261109")
            r=compare([doc],root)
            self.assertEqual(r["pilot_slots_reserved"],1)
            self.assertEqual(r["pending_result_codes"],["202611090101"])
            self.assertEqual(r["top1_by_phase"]["pilot"]["hit"]["denominator"],0)
            self.assertEqual(r["top1_by_phase"]["pilot"]["hit"]["original_pct"],None)
            self.assertFalse(r["candidate_first_remote_receipt_verified"])

    def test_nov9_gained_and_lost_both_counted_without_top3_change(self):
        for side in ("original","candidate"):
            with self.subTest(side=side),tempfile.TemporaryDirectory() as d:
                root=Path(d);doc=frozen(root,"20261109")
                row=doc["records"][0]
                old=row["baseline"]["hit"][0]
                new=row["top1_pair_candidate"]["hit"][0]
                self.assertNotEqual(old,new)
                self.assertEqual(set(row["baseline"]["hit"][:3]),
                                 set(row["top1_pair_candidate"]["hit"][:3]))
                result(root,row["race_code"],old if side=="original" else new)
                r=compare([doc],root)
                m=r["top1_by_phase"]["pilot"]["hit"]
                self.assertEqual(m["denominator"],1)
                if side=="original":
                    self.assertEqual((m["original"],m["candidate"],m["gained"],m["lost"]),(1,0,0,1))
                else:
                    self.assertEqual((m["original"],m["candidate"],m["gained"],m["lost"]),(0,1,1,0))
                self.assertFalse(r["formal"])

    def test_result_before_deadline_invalid_not_a_loss(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);doc=frozen(root,"20261109")
            row=doc["records"][0]
            result(root,row["race_code"],row["baseline"]["hit"][0],
                   confirmed_at="2026-11-09T08:00:00+09:00")
            r=compare([doc],root)
            self.assertEqual(r["invalid_result_codes"],["202611090101"])
            self.assertEqual(r["top1_by_phase"]["pilot"]["hit"]["denominator"],0)

    def test_future_ineligible_race_must_not_be_backfilled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);doc=frozen(root,"20261109")
            row=doc["records"][0]
            row["status"]="ineligible"
            row["reason"]="original_remote_observation_not_verified"
            doc["frozen_count"]=0
            doc["ineligible_count"]=1
            with self.assertRaisesRegex(ValueError,
                                         "top1_incomplete_frozen_cohort_no_replacement"):
                compare([doc],root)

    def test_tampered_candidate_rejected_before_result_read(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);doc=frozen(root,"20261109")
            doc["records"][0]["top1_pair_candidate"]["hit"][0]="6-5-4"
            with self.assertRaisesRegex(ValueError,"saved_candidate_not_reproducible"):
                compare([doc],root)


if __name__ == "__main__":
    unittest.main()
