"""Never use post-result information to enroll the actual Nov5 shadow cohort."""
import json
import tempfile
import unittest
from pathlib import Path

from nov05_saved_hole_shadow_audit import (
    RUN_ID, RUN_HEAD_SHA, PUBLICATION_SHA, PRE, OK, PENDING,
    EXPECTED_PUBLICATION, metadata_guard, _common_codes, run,
)

CODES = [f"20261105{venue:02d}{race:02d}"
         for venue in range(1, 10) for race in range(1, 13)][:106]


class SavedActualShadowAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.evidence = self.root / "capture" / "four-mode-evidence"
        self.evidence.mkdir(parents=True)
        self.metadata = {"id": RUN_ID, "name": "Four-mode prospective capture (research only)",
                         "event": "schedule", "head_branch": "main",
                         "head_sha": RUN_HEAD_SHA, "status": "completed",
                         "conclusion": "success"}
        self.publication = {"outcome": "pushed_to_main", "commit_sha": PUBLICATION_SHA,
                            "added_forecasts": EXPECTED_PUBLICATION}
        self.shadow = {"publication_commit_sha": PUBLICATION_SHA,
                       "published_new_count": EXPECTED_PUBLICATION,
                       "frozen_count": EXPECTED_PUBLICATION,
                       "validation_error_count": 0,
                       "records": [{"race_code": c} for c in CODES]}
        self.remote = {"publication_commit_sha": PUBLICATION_SHA,
                       "publication_count": EXPECTED_PUBLICATION,
                       "observed_before_t_minus_12": EXPECTED_PUBLICATION,
                       "observed_after_t_minus_12": 0, "unverified_count": 0,
                       "records": [{"race_code": c} for c in CODES]}
        self.links = {"checked": EXPECTED_PUBLICATION,
                      "hashes_present": EXPECTED_PUBLICATION,
                      "day_jst": "20261105",
                      "rows": [{"race_code": c, "status": "both_hashes_present",
                                "matches": {"race_cards": True, "title": True},
                                "independent_source_authenticity_verified": False}
                               for c in CODES]}
        self.events = []

    def save(self):
        for name, data in [
            ("publication.json", self.publication),
            ("hole-shadow.json", self.shadow),
            ("github-server-observation.json", self.remote),
            ("source-links.json", self.links)
        ]:
            (self.evidence / name).write_text(json.dumps(data), encoding="utf-8")
        self.metadata_file = self.root / "run.json"
        self.metadata_file.write_text(json.dumps(self.metadata), encoding="utf-8")

    def scorer(self, code, root, publication, hole_shadow, observation, *,
               git, score_outcome):
        if not score_outcome:
            self.events.append(("pre", code))
            return {"race_code": code, "status": PRE,
                    "deadline_jst": "2026-11-05T15:20:00+09:00",
                    "source_sha256": "a" * 64,
                    "baseline_top10": ["1-2-3"], "candidate_top10": ["1-3-2"]}
        self.events.append(("result", code))
        if CODES.index(code) >= 88:
            return {"race_code": code, "status": PENDING}
        i = CODES.index(code)
        baseline = i < 30
        candidate = i < 35
        return {"race_code": code, "status": OK, "topn": {
            f"top{k}": {"baseline": baseline, "candidate": candidate,
                        "gained": candidate and not baseline,
                        "lost": baseline and not candidate}
            for k in (1, 3, 5, 10)}}

    def test_106_pre_result_checked_before_any_88_outcomes(self):
        self.save()
        result = run(self.root, self.evidence.parent, self.metadata_file,
                     inspector=self.scorer)
        self.assertEqual(result["status"], "saved_candidate_result_comparison_research_only")
        self.assertEqual(result["published_frozen"], 106)
        self.assertEqual(result["pre_result_consistent"], 106)
        self.assertEqual(result["confirmed_result_content_scored"], 88)
        self.assertEqual(len(result["pending_result_codes"]), 18)
        self.assertEqual(len(result["per_race_result_diagnostic"]), 88)
        self.assertTrue(all(stage == "pre" for stage, _ in self.events[:106]))
        self.assertTrue(all(stage == "result" for stage, _ in self.events[106:]))
        self.assertEqual(result["paired_historical_topn"]["top10"]["baseline_hits"], 30)
        self.assertEqual(result["paired_historical_topn"]["top10"]["candidate_hits"], 35)
        self.assertEqual(result["paired_historical_topn"]["top10"]["gained"], 5)
        self.assertFalse(result["fixed_300_primary_study_complete"])
        self.assertIsNone(result["study_efficacy_p_value"])
        self.assertFalse(result["model_improvement_proven"])
        self.assertFalse(result["formal"])

    def test_forged_schedule_run_rejected(self):
        self.metadata["event"] = "pull_request"
        with self.assertRaisesRegex(ValueError, "untrusted_capture_run_provenance"):
            metadata_guard(self.metadata)

    def test_source_links_incomplete_rejected_before_outcomes(self):
        self.links["hashes_present"] = 105
        with self.assertRaisesRegex(ValueError, "actions_capture_batch_provenance"):
            _common_codes(self.publication, self.shadow, self.remote, self.links)

    def test_wrong_day_or_duplicate_race_rejected(self):
        self.shadow["records"][0]["race_code"] = "202611040101"
        with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_frozen_race_code"):
            _common_codes(self.publication, self.shadow, self.remote, self.links)
        self.shadow["records"][0]["race_code"] = CODES[1]
        with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_frozen_race_code"):
            _common_codes(self.publication, self.shadow, self.remote, self.links)

    def test_missing_saved_candidate_invalidates_entire_batch(self):
        self.save()
        def bad(code, root, publication, hole_shadow, observation, *, git, score_outcome):
            if not score_outcome and code == CODES[0]:
                return {"race_code": code, "status": "excluded_unverified_evidence",
                        "reason": "shadow_not_frozen"}
            return self.scorer(code, root, publication, hole_shadow, observation,
                               git=git, score_outcome=score_outcome)
        result = run(self.root, self.evidence.parent, self.metadata_file,
                     inspector=bad)
        self.assertEqual(result["status"], "pre_result_evidence_rejected")
        self.assertIsNone(result["historical_paired_topn"])
        self.assertEqual(len(result["pre_result_rejected"]), 1)
        self.assertFalse(any(k == "result" for k, _ in self.events))


if __name__ == "__main__":
    unittest.main()
