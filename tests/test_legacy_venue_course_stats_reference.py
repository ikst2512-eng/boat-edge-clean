"""Contract: imported historical course rates must be exact original blobs, not a silent model change."""
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research" / "legacy_course_stats_reference"
NAMES = [f"{i:02d}.json" for i in range(1, 25)] + ["index.json"]

def git_blob_sha(payload):
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\\0" + payload).hexdigest()

class LegacyVenueCourseReferenceTests(unittest.TestCase):
    def test_all_twenty_four_sites_match_original_git_objects(self):
        manifest = json.loads((DATA / "import_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["original_repo"], "ikst2512-eng/boat-edge")
        self.assertEqual(manifest["source_commit"], "7dd4ce6127d7e71298605015873030ff1168a8d3")
        self.assertEqual(set(manifest["file_blob_sha"]), set(NAMES))
        self.assertTrue(manifest["reference_only"])
        self.assertFalse(manifest["original_prediction_logic_uses_course_stats"])
        for name in NAMES:
            with self.subTest(name=name):
                path = DATA / name
                self.assertTrue(path.is_file())
                raw = path.read_bytes()
                digest = hashlib.sha1(
                    b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw
                ).hexdigest()
                self.assertEqual(digest, manifest["file_blob_sha"][name])
                data = json.loads(raw)
                if name == "index.json":
                    self.assertEqual(data["venues_ok"], 24)
                    self.assertEqual(data["venues_total"], 24)
                    self.assertFalse(data["prediction_logic_uses_course_stats"])
                    continue
                venue = name[:2]
                self.assertEqual(data["venue_code"], venue)
                self.assertEqual(data["source_url"], "https://www.boatrace.jp/owpc/pc/data/stadium?jcd=" + venue)
                self.assertEqual(data["period"], {"from": "2026/07/01", "to": "2026/09/30"})
                self.assertEqual(data["unit"], "percent")
                self.assertFalse(data["prediction_logic_uses_course_stats"])
                self.assertEqual(data["method_rate_meaning"], "share_of_winning_methods_within_each_course")
                self.assertEqual(set(data["courses"]), set(map(str, range(1, 7))))
                for lane in map(str, range(1, 7)):
                    row = data["courses"][lane]
                    for field in ("first_rate", "second_rate", "third_rate", "escape", "sashi", "makuri", "makuri_sashi"):
                        value = row[field]
                        self.assertIs(type(value), (int if type(value) is int else float))
                        self.assertTrue(math.isfinite(value) and 0 <= value <= 100)
    def test_data_is_not_injected_into_active_model(self):
        model = (ROOT / "legacy_v133_reference_engine.py").read_text(encoding="utf-8")
        self.assertIn('legacy_v133_course_stats_not_imported', model)
        self.assertNotIn('legacy_course_stats_reference', model)

if __name__ == "__main__":
    unittest.main()
