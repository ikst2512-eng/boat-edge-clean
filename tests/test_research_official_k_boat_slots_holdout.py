"""Offline boat-number role comparison safety tests; no collection or forecast run."""
from copy import deepcopy
from datetime import date, timedelta
import unittest

from scripts.research_official_k_c2_athlete_chronological_holdout import losses_for_target
from scripts.research_official_k_boat_slots_holdout import EXPECTED_COUNTS

def small_cohort():
    train = []
    test = []
    for i in range(90):
        train.append({
            "venue": "01" if i % 3 else "02",
            "c1_registration": "1111" if i % 2 else "1112",
            "c2_registration": "2221" if i % 3 else "2222",
            "boat1_registration": "1111" if i % 4 else "2221",
            "boat2_registration": "2221" if i % 5 else "1112",
            "c1_escape": int(i % 4 == 0),
            "c2_sashi": int(i % 13 == 0),
        })
    for i in range(31):
        test.append({
            "day": (date(2026, 10, 1) + timedelta(days=i)).strftime("%Y%m%d"),
            "venue": "01" if i % 3 else "02",
            "c1_registration": "1111" if i % 2 else "1112",
            "c2_registration": "2221" if i % 3 else "2222",
            "boat1_registration": "1111" if i % 4 else "2221",
            "boat2_registration": "2221" if i % 5 else "1112",
            "c1_escape": int(i % 4 == 0),
            "c2_sashi": int(i % 13 == 0),
        })
    return train, test

class TestBoatSlotHistory(unittest.TestCase):
    def test_same_train_test_different_identity_roles(self):
        train,test = small_cohort()
        a = losses_for_target(train,test,"c1_escape","actual_course")
        b = losses_for_target(train,test,"c1_escape","boat_number")
        self.assertEqual(a["holdout_n"],31)
        self.assertEqual(b["holdout_n"],31)
        self.assertEqual(a["models"]["venue"],b["models"]["venue"])
        self.assertNotEqual(a["models"]["venue_plus_c1"],b["models"]["venue_plus_c1"])

    def test_roles_are_explicit_and_not_swappable_by_untrusted_string(self):
        train,test = small_cohort()
        with self.assertRaisesRegex(ValueError, "unsupported_identity_role"):
            losses_for_target(train,test,"c1_escape","test_outcome")

    def test_train_only_october_label_leakage_rejected_by_design(self):
        train,test = small_cohort()
        a = losses_for_target(train,test,"c2_sashi","boat_number")
        after = [dict(x,c2_sashi=1-x["c2_sashi"]) for x in test]
        b = losses_for_target(train,after,"c2_sashi","boat_number")
        self.assertEqual(a["training_target_rate"],b["training_target_rate"])
        self.assertNotEqual(a["models"]["venue"]["observed_rate"],b["models"]["venue"]["observed_rate"])

    def test_unseen_boat2_identity_gets_zero_residual(self):
        train,test = small_cohort()
        future = [dict(x,boat2_registration="9999") for x in test]
        x = losses_for_target(train,future,"c1_escape","boat_number")
        self.assertEqual(x["holdout_c2_seen_in_train"],0)
        self.assertEqual(x["models"]["venue_plus_c2"],x["models"]["venue"])

    def test_invariant_role_mismatch_counts(self):
        self.assertEqual(EXPECTED_COUNTS, {
            "eligible":13815,"train":9241,"holdout":4574,
            "boat1_vs_actual_c1_mismatch":116,
            "boat2_vs_actual_c2_mismatch":706
        })

    def test_paired_bootstrap_deterministic_in_boat_mode(self):
        train,test=small_cohort()
        a=losses_for_target(train,test,"c1_escape","boat_number")
        b=losses_for_target(train,test,"c1_escape","boat_number")
        self.assertEqual(a["paired_October_day_bootstrap"],b["paired_October_day_bootstrap"])

    def test_keep_old_actual_course_mode_default_equivalent(self):
        train,test=small_cohort()
        a=losses_for_target(train,test,"c2_sashi")
        b=losses_for_target(train,test,"c2_sashi","actual_course")
        self.assertEqual(a,b)

if __name__ == "__main__":
    unittest.main()
