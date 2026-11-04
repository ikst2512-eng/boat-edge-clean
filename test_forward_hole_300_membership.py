"""Synthetic regression tests for result-blind first-300 membership."""
import copy
import unittest
from forward_hole_300_membership import build_pre_result_membership
from forward_hole_rank3_protocol import validate

BASE = ["1-2-3", "1-2-4", "1-3-2", "2-3-1", "2-3-4",
        "3-4-1", "3-4-2", "1-2-5", "2-3-5", "3-4-5"]
CANDIDATE = ["1-2-3", "1-2-4", "1-4-2", "1-3-2", "2-3-1",
             "2-3-4", "3-4-1", "3-4-2", "1-2-5", "3-4-5"]


def protocol_receipt():
    return {
        "schema": "FOUR_MODE_RESEARCH_PROTOCOL_GITHUB_SERVER_OBSERVATION_V1",
        "status": "research_protocol_on_github_before_study_cutoff",
        "protocol_commit_sha": "c" * 40,
        "protocol_file": "research/forward_hole_rank3_protocol_20261105.json",
        "protocol_sha256": validate()["protocol_sha256"],
        "github_server_date_utc": "2026-11-04T20:14:25+00:00",
        "predeclared_observation_deadline_jst": "2026-11-05T07:00:00+09:00",
        "server_response_not_first_receipt_proof": True,
        "observed_protocol_only_not_forecasts": True,
        "formal": False, "remote_forecasts_verified": False,
        "eligible_races_proven": False, "production_promotion_allowed": False,
    }


def row(code):
    y, mo, d = code[:4], code[4:6], code[6:8]
    return {
        "race_code": code, "status": "pre_result_evidence_consistent_research_only",
        "deadline_jst": f"{y}-{mo}-{d}T12:00:00+09:00",
        "source_git_commit_sha": "d" * 40,
        "source_sha256": "e" * 64,
        "github_server_observed_at_utc": f"{y}-{mo}-{d}T00:00:00+00:00",
        "baseline_top10": list(BASE),
        "candidate_top10": list(CANDIDATE),
        "formal": False, "first_remote_receipt_verified": False,
        "capture_run_inventory_verified": False,
        "original_actions_artifact_origin_authenticated": False,
        "result_accessed": False,
        "warning": "Pre-result only, not yet official provenance certified",
    }


def sample(n):
    codes = [f"20261105{v:02d}{race:02d}"
             for v in range(1, 25) for race in range(1, 13)]
    codes += [f"20261106{v:02d}{race:02d}"
              for v in range(1, 25) for race in range(1, 13)]
    return [row(code) for code in codes[:n]]


class PreResultEnrollmentTests(unittest.TestCase):
    def test_first_300_race_ids_frozen_without_any_finish(self):
        items = sample(301)
        result = build_pre_result_membership(list(reversed(items)),
                                             protocol_receipt())
        self.assertEqual(result["status"], "provisional_first_300_pre_result_members_identified")
        self.assertEqual(result["observed_pre_result_candidates"], 301)
        self.assertEqual(result["enrolled_members"], 300)
        self.assertEqual(result["over_cap_non_enrolled"], 1)
        self.assertEqual(result["roster_codes"], [x["race_code"] for x in items[:300]])
        self.assertNotIn(items[300]["race_code"], result["roster_codes"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["model_improvement_proven"])
        self.assertFalse(result["roster_committed_before_any_result"])
        self.assertTrue(result["no_outcome_consulted"])
        self.assertIsNone(result["efficacy_p_value"])
        self.assertEqual(len(result["roster_sha256"]), 64)
        self.assertEqual(len(result["exact_frozen_ticket_membership_sha256"]), 64)

    def test_less_than_300_is_pending_not_a_failed_race(self):
        out = build_pre_result_membership(sample(299), protocol_receipt())
        self.assertEqual(out["status"], "awaiting_300_pre_result_members")
        self.assertEqual(out["enrolled_members"], 299)
        self.assertIsNone(out["efficacy_p_value"])
        self.assertFalse(out["production_promotion_allowed"])

    def test_zero_is_not_zero_hit_accuracy(self):
        out = build_pre_result_membership([], protocol_receipt())
        self.assertEqual(out["enrolled_members"], 0)
        self.assertFalse(out["formal"])
        self.assertNotIn("hit_rate_pct", out)

    def test_winner_or_payout_field_disqualifies_enrollment(self):
        items = sample(1)
        items[0]["winning_ticket"] = "1-4-2"
        with self.assertRaisesRegex(ValueError, "unexpected_pre_result_fields"):
            build_pre_result_membership(items, protocol_receipt())
        items[0].pop("winning_ticket")
        items[0]["payout"] = 9999
        with self.assertRaisesRegex(ValueError, "unexpected_pre_result_fields"):
            build_pre_result_membership(items, protocol_receipt())

    def test_pending_results_cannot_make_later_race_first(self):
        items = sample(301)
        one = build_pre_result_membership(items, protocol_receipt())
        two = build_pre_result_membership(list(reversed(items)), protocol_receipt())
        self.assertEqual(one["roster_sha256"], two["roster_sha256"])
        self.assertEqual(one["roster_codes"], two["roster_codes"])

    def test_duplicate_race_rejected_even_if_same_original(self):
        items = sample(2)
        with self.assertRaisesRegex(ValueError, "duplicate_original_race"):
            build_pre_result_membership([items[0], items[0]], protocol_receipt())

    def test_bad_early_receipt_rejected(self):
        receipt = protocol_receipt()
        receipt["github_server_date_utc"] = "2026-11-04T22:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "protocol_observation_not_pre_study"):
            build_pre_result_membership(sample(1), receipt)

    def test_invalid_timestamp_or_pre_result_flag_rejected(self):
        items = sample(1)
        items[0]["deadline_jst"] = "2026-11-05T12:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "unexpected_timezone"):
            build_pre_result_membership(items, protocol_receipt())
        items = sample(1)
        items[0]["result_accessed"] = True
        with self.assertRaisesRegex(ValueError, "pre_result_gate_not_passed"):
            build_pre_result_membership(items, protocol_receipt())

    def test_untrusted_ticket_mutation_rejected(self):
        items = sample(1)
        items[0]["candidate_top10"][0] = "6-5-4"
        with self.assertRaisesRegex(ValueError, "changed_predeclared_budget_or_pair_coverage"):
            build_pre_result_membership(items, protocol_receipt())

    def test_out_of_window_not_enrolled(self):
        items = sample(1)
        items[0]["race_code"] = "202611040101"
        with self.assertRaisesRegex(ValueError, "outside_predeclared_period"):
            build_pre_result_membership(items, protocol_receipt())


if __name__ == "__main__":
    unittest.main()
