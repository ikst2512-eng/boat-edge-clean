import unittest
from pathlib import Path
from unittest.mock import patch

from hole_locked_two_pair_miss_audit import (
    source_bucket,third_donor_state,inspect)
from test_hole_third_choice_research import archive as archive_fixture

CODES=["202611030101","202611030102","202611030103",
       "202611030104","202611030105","202611030106"]
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
      "2-1-3","1-4-5","1-2-5","1-3-5","1-2-6"]
LOCKED=BASE[:5]+["1-5-3","1-6-3"]+BASE[5:8]


def fixture():
    a=archive_fixture()
    a["modes"]["hole"]["tickets"]=[{"combo":t,"p":1}
                                      for t in BASE+["1-6-2"]]
    a["modes"]["hit"]["tickets"]=[
        {"combo":t,"p":1} for t in (
            "1-5-3","1-5-2","1-6-3","1-6-2","1-2-6")]
    a["modes"]["balance"]["tickets"]=[
        {"combo":t,"p":1} for t in ("1-5-3","1-6-3","1-4-6","2-3-1")]
    return a


class LockedTwoPairMissTests(unittest.TestCase):
    def test_source_classification_is_mutually_exclusive(self):
        a=fixture()
        self.assertEqual(source_bucket(a,"1-6-4"),"hole_tail")
        self.assertEqual(source_bucket(a,"1-5-4"),"both_donors")
        self.assertEqual(source_bucket(a,"1-4-6"),"balance_only")
        self.assertEqual(source_bucket(a,"2-1-3"),"no_saved_candidate")
        self.assertEqual(third_donor_state(a,"1-5-2"),
                         "exact_ticket_in_donors")
        self.assertEqual(third_donor_state(a,"1-5-4"),
                         "pair_only_in_donors")
        self.assertEqual(third_donor_state(a,"1-3-6"),
                         "no_donor_pair")

    def test_all_miss_types_reconcile_before_and_after_locked(self):
        a=fixture();events=[]
        winners=["1-5-3","1-2-6","1-5-2","2-3-1","4-1-3","1-4-6"]
        def selected(archive,rates):
            events.append("select")
            return {"baseline":BASE,"third_national_rate":LOCKED}
        def result(code,root):
            events.append("result")
            return {"status":"historical_comparison_only",
                    "winning_ticket":winners[CODES.index(code)]}
        with patch("hole_locked_two_pair_miss_audit.archived_four_modes",
                   return_value=(200,a)),patch(
             "hole_locked_two_pair_miss_audit.national_rates",return_value=None),patch(
             "hole_locked_two_pair_miss_audit.variants",side_effect=selected),patch(
             "hole_locked_two_pair_miss_audit.compare_race",side_effect=result):
            report=inspect(CODES,Path("."))
        self.assertEqual(events,["select","result"]*6)
        self.assertEqual(report["comparable"],6)
        self.assertEqual(report["miss_classes"],{
            "hit":1,"first_head_absent":1,
            "second_pair_absent":1,"third_boat_absent":3})
        self.assertEqual(report["gain_loss"],{
            "rescued":1,"displaced":1,"net":0})
        self.assertEqual(report["missing_pair_sources"]["balance_only"],1)
        self.assertEqual(
            report["wrong_third_donor_availability"]["exact_ticket_in_donors"],3)
        self.assertEqual(sum(report["miss_classes"].values()),6)
        self.assertEqual(sum(report["by_date"][CODES[0][:8]][k]
                             for k in ("hit","first_head_absent",
                                       "second_pair_absent","third_boat_absent")),6)

    def test_unconfirmed_excluded_and_does_not_inflate_misses(self):
        with patch("hole_locked_two_pair_miss_audit.archived_four_modes",
                   return_value=(200,fixture())),patch(
             "hole_locked_two_pair_miss_audit.national_rates",return_value=None),patch(
             "hole_locked_two_pair_miss_audit.variants",
             return_value={"baseline":BASE,"third_national_rate":LOCKED}),patch(
             "hole_locked_two_pair_miss_audit.compare_race",
             return_value={"status":"unconfirmed"}):
            report=inspect([CODES[0]],Path("."))
        self.assertEqual(report["comparable"],0)
        self.assertEqual(report["excluded"]["unconfirmed_result"],1)
        self.assertEqual(sum(report["miss_classes"].values()),0)

    def test_invalid_frozen_prefix_rejected(self):
        with patch("hole_locked_two_pair_miss_audit.archived_four_modes",
                   return_value=(200,fixture())),patch(
             "hole_locked_two_pair_miss_audit.national_rates",return_value=None),patch(
             "hole_locked_two_pair_miss_audit.variants",
             return_value={"baseline":BASE,"third_national_rate":BASE[::-1]}):
            with self.assertRaisesRegex(ValueError,"locked_top5_budget"):
                inspect([CODES[0]],Path("."))


if __name__=="__main__":
    unittest.main()
