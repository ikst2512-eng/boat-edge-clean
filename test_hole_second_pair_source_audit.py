import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hole_second_pair_source_audit import provenance,inspect

CODES=["202611030101","202611030102","202611030103",
       "202611030104","202611030105","202611030106"]
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
      "1-4-3","1-4-5","1-2-5","1-3-5","1-2-6"]


def fake_archive(kind):
    hole=BASE[:]
    hit=["1-5-3","1-5-2"]
    balance=["1-5-4"]
    if kind=="tail":
        hole.append("1-5-2")
    if kind=="donors_both":
        hit.append("1-6-2")
        balance.append("1-6-3")
    if kind=="donor_hit":
        hit.append("1-6-2")
    return {"modes":{
        "hole":{"tickets":[{"combo":t,"p":1} for t in hole]},
        "hit":{"tickets":[{"combo":t,"p":1} for t in hit]},
        "balance":{"tickets":[{"combo":t,"p":1} for t in balance]}}}


class SourceAuditTests(unittest.TestCase):
    def test_missing_feature_flags_are_not_imputed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"four_mode_forecasts"
            folder.mkdir()
            (folder/(CODES[0]+".json")).write_text(json.dumps({
                "beforeinfo":"optional_not_in_snapshot",
                "input_national_win_rates":[1,2,3,4,5,6],
                "source_sha256":{"race_cards":"abc"}}))
            recorded=provenance(CODES[0],tmp)
            self.assertEqual(recorded["beforeinfo"],"not_in_snapshot")
            self.assertTrue(recorded["six_national_rates_present"])
            self.assertFalse(recorded["raw_exhibition_present"])
            self.assertFalse(recorded["raw_entry_present"])
            self.assertFalse(recorded["raw_course_statistics_present"])
            self.assertTrue(recorded["source_hashes_present"])

    def test_six_coverage_paths_and_no_result_data_before_score(self):
        archives={
            CODES[0]:fake_archive("tail"),
            CODES[1]:fake_archive("donors_both"),
            CODES[2]:fake_archive("donor_hit"),
            CODES[3]:fake_archive("none"),
            CODES[4]:fake_archive("none"),
            CODES[5]:fake_archive("none"),
        }
        outcomes={
            CODES[0]:"1-5-6", # existing hole tail pair
            CODES[1]:"1-6-4", # donor both
            CODES[2]:"1-6-5", # donor hit only
            CODES[3]:"1-6-3", # no donor match for pair
            CODES[4]:"4-1-2", # head absent
            CODES[5]:"1-2-5", # top10 hit
        }
        events=[]
        def get_archive(code,root):
            events.append(("archive",code))
            return 200,archives[code]
        def get_result(code,root):
            events.append(("result",code))
            return {"status":"historical_comparison_only",
                    "winning_ticket":outcomes[code]}
        with patch("hole_second_pair_source_audit.archived_four_modes",
                   side_effect=get_archive),patch(
             "hole_second_pair_source_audit.provenance",
             return_value={"beforeinfo":"not_in_snapshot",
                           "raw_exhibition_present":False}),patch(
             "hole_second_pair_source_audit.compare_race",
             side_effect=get_result):
            result=inspect(CODES,Path("."))
        self.assertEqual(result["comparable"],6)
        self.assertEqual(result["miss_classes"]["pair_missing"],4)
        self.assertEqual(result["miss_classes"]["head_missing"],1)
        self.assertEqual(result["miss_classes"]["top10_hit"],1)
        self.assertEqual(result["missing_pair_location"]["hole_tail_pair"],1)
        self.assertEqual(result["missing_pair_location"]["both_donor_modes_only"],1)
        self.assertEqual(result["missing_pair_location"]["hit_donor_only"],1)
        self.assertEqual(result["missing_pair_location"]["absent_all_frozen_modes"],1)
        for code in CODES:
            self.assertLess(events.index(("archive",code)),
                            events.index(("result",code)))
        self.assertEqual(len(result["examples"]),4)

    def test_unconfirmed_results_do_not_count_as_misses(self):
        with patch("hole_second_pair_source_audit.archived_four_modes",
                   return_value=(200,fake_archive("none"))),patch(
             "hole_second_pair_source_audit.compare_race",
             return_value={"status":"unconfirmed"}):
            out=inspect([CODES[0]],Path("."))
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["excluded"]["unconfirmed_result"],1)
        self.assertEqual(out["miss_classes"]["pair_missing"],0)

    def test_source_symlink_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"four_mode_forecasts";folder.mkdir()
            src=Path(tmp)/"data.json";src.write_text("{}")
            (folder/(CODES[0]+".json")).symlink_to(src)
            with self.assertRaises(ValueError):
                provenance(CODES[0],tmp)


if __name__=="__main__":
    unittest.main()
