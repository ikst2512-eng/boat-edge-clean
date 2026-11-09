"""Structural projection tests; synthetic bytes and stub replay are NOT official."""
import base64
import copy
import hashlib
import json
import unittest
from itertools import permutations

from scenario_official_exhibition_projection import project_exhibition_research

STAGES = [
    "preflight_raw_byte_sha_and_clock_structure",
    "official_racelist_six_registration_parser",
    "official_beforeinfo_six_exhibition_start_parser",
    "official_120_odds_html_parser",
    "declared_normalized_features_match_raw_reparse",
]


def replay_stub(source_bundle, candidate):
    # This synthetic callback proves only adapter compatibility, never
    # independently attested official bytes or the real #1693 parser.
    return {
        "schema": "FOUR_MODE_OFFICIAL_RAW_SEMANTIC_REPLAY_V1",
        "race_code": source_bundle["race_code"],
        "status": "raw_bytes_semantically_reparsed_and_declared_features_match_RESEARCH_ONLY",
        "verified_stages": list(STAGES),
        "formal": False, "model_promotion_allowed": False,
        "raw_official_provenance_independently_attested": False,
        "actual_model_output_independently_replayed": False,
        "first_remote_candidate_acceptance_independently_verified": False,
    }


def fixture():
    code = "202611091710"
    originals = {}
    hashes = {}
    for i, kind in enumerate(("racelist", "beforeinfo", "odds120")):
        raw = ("SYNTHETIC NOT BOATRACE:" + kind).encode()
        digest = hashlib.sha256(raw).hexdigest()
        hashes[kind] = digest
        originals[kind] = {
            "raw_base64": base64.b64encode(raw).decode("ascii"),
            "sha256": digest,
            "source_url": "https://www.boatrace.jp/mock/" + kind,
            "received_at_jst": "2026-11-09T15:0" + str(i + 1) + ":00+09:00",
        }
    norm = {
        "race_code": code,
        "source_sha256": hashes,
        "racelist_registration_ids": [str(x) for x in range(4510, 4516)],
        "beforeinfo_registration_ids": [str(x) for x in range(4510, 4516)],
        "exhibition_courses": [1, 2, 3, 4, 5, 6],
        "exhibition_times": [6.80, 6.69, 6.75, 6.78, 6.76, 6.81],
        "exhibition_st": [0.12, 0.06, 0.18, 0.11, 0.15, 0.16],
        "exhibition_tilts": [0.0] * 6,
        "odds_3t": {
            "-".join(map(str, t)): 10.0
            for t in permutations(range(1, 7), 3)
        },
    }
    source = {
        "schema": "FOUR_MODE_FUTURE_OFFICIAL_INPUT_LINEAGE_PREFLIGHT_V1",
        "race_code": code,
        "deadline_jst": "2026-11-09T15:30:00+09:00",
        "originals": originals,
        "normalized_source_claim": norm,
    }
    digest = hashlib.sha256(json.dumps(
        norm, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")
    ).encode()).hexdigest()
    candidate = {
        "race_code": code,
        "deadline_jst": source["deadline_jst"],
        "generated_at_jst": "2026-11-09T15:07:00+09:00",
        "consumed_source_sha256": hashes.copy(),
        "consumed_normalized_claim_sha256": digest,
        "formal": False,
    }
    return source, candidate


class ExhibitionProjectionTests(unittest.TestCase):
    def setUp(self):
        self.source, self.candidate = fixture()

    def project(self, source=None, candidate=None, callback=replay_stub):
        return project_exhibition_research(
            self.source if source is None else source,
            self.candidate if candidate is None else candidate, callback)

    def test_six_boat_exhibition_only_all_other_features_unknown(self):
        before = copy.deepcopy((self.source, self.candidate))
        result = self.project()
        self.assertEqual(len(result["exhibition_features_by_boat"]), 6)
        self.assertEqual(result["exhibition_features_by_boat"][1]["exhibition_st_s"], .06)
        self.assertEqual(result["exhibition_features_by_boat"][0]["exhibition_course_only"], 1)
        self.assertIn("tide_height_cm", result["missing_research_features"])
        self.assertIn("wind_speed_mps", result["missing_research_features"])
        self.assertIn("actual_entry_course", result["missing_research_features"])
        for flag in ("formal", "accuracy_effect_proven", "production_changed",
                     "candidate_first_remote_receipt_verified",
                     "model_consumed_these_features_verified",
                     "raw_http_origin_independently_attested",
                     "replay_callback_authenticity_independently_proven"):
            self.assertFalse(result[flag])
        self.assertFalse(result["exhibition_is_actual_final_entry"])
        self.assertEqual(before, (self.source, self.candidate))

    def test_cross_race_and_wrong_deadline_fail(self):
        c = copy.deepcopy(self.candidate)
        c["race_code"] = "202611091711"
        with self.assertRaises(ValueError):
            self.project(candidate=c)
        c = copy.deepcopy(self.candidate)
        c["deadline_jst"] = "2026-11-09T16:00:00+09:00"
        with self.assertRaises(ValueError):
            self.project(candidate=c)

    def test_stale_or_post_cutoff_evidence_rejected(self):
        s = copy.deepcopy(self.source)
        s["originals"]["beforeinfo"]["received_at_jst"] = "2026-11-09T15:19:00+09:00"
        with self.assertRaises(ValueError):
            self.project(source=s)
        c = copy.deepcopy(self.candidate)
        c["generated_at_jst"] = "2026-11-09T15:19:00+09:00"
        with self.assertRaises(ValueError):
            self.project(candidate=c)
        c = copy.deepcopy(self.candidate)
        c["generated_at_jst"] = "2026-11-09T15:02:30+09:00"
        with self.assertRaises(ValueError):
            self.project(candidate=c)

    def test_original_raw_byte_and_declared_digest_must_match(self):
        s = copy.deepcopy(self.source)
        s["originals"]["odds120"]["raw_base64"] = base64.b64encode(b"changed").decode()
        with self.assertRaises(ValueError):
            self.project(source=s)
        s = copy.deepcopy(self.source)
        s["normalized_source_claim"]["source_sha256"]["beforeinfo"] = "a" * 64
        with self.assertRaises(ValueError):
            self.project(source=s)
        c = copy.deepcopy(self.candidate)
        c["consumed_normalized_claim_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.project(candidate=c)

    def test_six_boat_and_official_full_odds_must_exist(self):
        s = copy.deepcopy(self.source)
        s["normalized_source_claim"]["exhibition_courses"] = [1, 1, 3, 4, 5, 6]
        with self.assertRaises(ValueError):
            self.project(source=s)
        s = copy.deepcopy(self.source)
        s["normalized_source_claim"]["exhibition_st"] = [0.01] * 5
        with self.assertRaises(ValueError):
            self.project(source=s)
        s = copy.deepcopy(self.source)
        s["normalized_source_claim"]["odds_3t"].pop("1-2-3")
        with self.assertRaises(ValueError):
            self.project(source=s)

    def test_result_or_formal_claim_fails_closed(self):
        s = copy.deepcopy(self.source)
        s["normalized_source_claim"]["result"] = "1-2-3"
        with self.assertRaises(ValueError):
            self.project(source=s)
        s = copy.deepcopy(self.source)
        s["originals"]["beforeinfo"]["payout"] = 2500
        with self.assertRaises(ValueError):
            self.project(source=s)
        c = copy.deepcopy(self.candidate)
        c["formal"] = True
        with self.assertRaises(ValueError):
            self.project(candidate=c)
        c = copy.deepcopy(self.candidate)
        c["final_entry_course"] = [1, 2, 3, 4, 5, 6]
        with self.assertRaises(ValueError):
            self.project(candidate=c)

    def test_replay_callback_failure_or_fake_validation_rejected(self):
        def wrong(source, candidate):
            record = replay_stub(source, candidate)
            record["raw_official_provenance_independently_attested"] = True
            return record
        with self.assertRaises(ValueError):
            self.project(callback=wrong)
        def no_odds(source, candidate):
            record = replay_stub(source, candidate)
            record["verified_stages"].remove("official_120_odds_html_parser")
            return record
        with self.assertRaises(ValueError):
            self.project(callback=no_odds)

    def test_no_callback_is_not_equivalent_to_parser_success(self):
        with self.assertRaises(ValueError):
            self.project(callback=None)


if __name__ == "__main__":
    unittest.main()
