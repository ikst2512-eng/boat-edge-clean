"""Research-only fail-closed feature-source gates; does not import model or CI."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.research_venue24_feature_readiness_gate import (
    SOURCE_PATHS, get_source, validate,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/research/venue24_feature_readiness_handoff_20261109.json"

def snapshot():
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    originals = {}
    for k in ("venue_baseline", "official_water_diagram",
              "diagram_single_Ai_view", "official_K_course2_counts"):
        e = doc["provenance"][k]
        originals[e["file"]] = get_source(ROOT, e["file"], e["git_blob_sha"])
    return doc, originals

class Venue24ReadinessTest(unittest.TestCase):
    def test_all_24_frozen_sources_and_unknowns(self):
        doc, raw = snapshot()
        r = validate(doc, raw)
        self.assertEqual((r["venues"],r["cohort_eligible"],r["approved_model_features"]),(24,13815,0))

    def test_refuse_synthetic_official_first_receipt(self):
        doc, raw = snapshot()
        doc["venues"][0]["feature_status"]["wind_speed_and_wave"]["predeadline_eligible"] = True
        with self.assertRaisesRegex(ValueError, "predeadline_evidence_missing"):
            validate(doc, raw)

    def test_refuse_false_survey_bearing(self):
        doc, raw = snapshot()
        doc["venues"][5]["feature_status"]["official_water_diagram"]["schematic_bearing_approved"] = True
        with self.assertRaisesRegex(ValueError, "original_png_or_arrow_gate"):
            validate(doc, raw)

    def test_refuse_tide_zero_substituted_for_missing(self):
        doc, raw = snapshot()
        doc["venues"][0]["feature_status"]["tide"]["measured_tide_height_at_race"] = 0
        with self.assertRaisesRegex(ValueError, "unobserved_tide_must_remain_unknown"):
            validate(doc, raw)

    def test_refuse_false_model_gain(self):
        doc, raw = snapshot()
        doc["venues"][0]["feature_status"]["course2_sashi"]["forecast_effect_proven"] = True
        with self.assertRaisesRegex(ValueError, "effect_unproved_must_be_false"):
            validate(doc, raw)

    def test_refuse_2c_proxy_as_athlete_escapement(self):
        doc, raw = snapshot()
        doc["venues"][0]["feature_status"]["course2_escape_proxy"]["is_athlete_specific_c2_escapement_rate"] = True
        with self.assertRaisesRegex(ValueError, "c2_proxy_vs_true_wall_mismatch"):
            validate(doc, raw)

    def test_refuse_cutting_one_venue(self):
        doc, raw = snapshot()
        doc["venues"] = doc["venues"][:-1]
        with self.assertRaisesRegex(ValueError, "venue_count_not_24"):
            validate(doc, raw)

    def test_refuse_changed_source_bytes(self):
        doc, raw = snapshot()
        raw = dict(raw)
        raw[SOURCE_PATHS[3]] += b"\n"
        with self.assertRaisesRegex(ValueError, "unmatched_source_git_blob"):
            validate(doc, raw)

    def test_refuse_unfrozen_original_artifact(self):
        doc, raw = snapshot()
        doc["provenance"]["official_K_raw_artifact_zip_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "official_K_original_artifact_sha_unfrozen"):
            validate(doc, raw)

    def test_refuse_duplicate_code(self):
        doc, raw = snapshot()
        doc["venues"][1]["venue_code"] = "01"
        with self.assertRaisesRegex(ValueError, "venue_codes_missing_or_duplicate"):
            validate(doc, raw)

    def test_source_refs_are_frozen(self):
        doc, raw = snapshot()
        self.assertEqual(set(raw), set(SOURCE_PATHS))
        self.assertEqual(doc["counts"]["priority_AI_compass_disagreement_venues"],["01","03","10","13","20","23","24"])

if __name__ == "__main__":
    unittest.main()
