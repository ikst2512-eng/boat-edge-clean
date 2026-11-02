import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_shadow_bundle_audit import audit

CODE="202611030101"
class ShadowAuditTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)
  (self.root/"four_mode_forecasts").mkdir()
  self.data=b"frozen-archive-bytes"
  (self.root/"four_mode_forecasts"/(CODE+".json")).write_bytes(self.data)
  self.p=self.root/"shadow.json"
  self.record={"race_code":CODE,"status":"shadow_frozen_unverified",
               "source_sha256":hashlib.sha256(self.data).hexdigest(),
               "deadline_jst":"2026-11-03T15:00:00+09:00",
               "baseline":["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2"],
               "shadow":["1-2-3","1-3-4","1-5-2","1-2-4","1-4-2"],
               "shadow_bundle2":["1-2-3","1-3-4","1-5-2","1-5-3","1-4-2"]}
  self.archive={"deadline_jst":self.record["deadline_jst"],
                "modes":{"hole":{"tickets":[{"combo":x} for x in self.record["baseline"]]},
                         "hit":{"tickets":[{"combo":"1-5-2"},{"combo":"1-5-3"}]},
                         "balance":{"tickets":[{"combo":"1-5-2"},{"combo":"1-5-3"}]}}
 def write(self):
  self.p.write_text(json.dumps({"status":"research_only_after_confirmed_push","records":[self.record]}))
 def test_comparison_separates_gained_and_lost(self):
  self.write()
  with patch("hole_shadow_bundle_audit.archived_four_modes",return_value=(200,self.archive)),patch(
      "hole_shadow_bundle_audit.compare_race",return_value={"status":"historical_comparison_only","winning_ticket":"1-5-3"}):
   r=audit(self.root,self.p)
  self.assertEqual(r["comparable"],1)
  self.assertEqual(r["delta"]["shadow_bundle2"]["top5"]["gained"],1)
  self.assertEqual(r["delta"]["shadow"]["top3"]["gained"],0)
  self.assertFalse(r["formal"])
 def test_tampered_bundle_excluded(self):
  self.record["shadow_bundle2"][3]="1-6-3";self.write()
  with patch("hole_shadow_bundle_audit.archived_four_modes",return_value=(200,self.archive)):
   r=audit(self.root,self.p)
  self.assertEqual(r["comparable"],0)
  self.assertEqual(r["excluded"][0]["reason"],"candidate_algorithm_mismatch")
 def test_hash_mismatch_excluded(self):
  self.record["source_sha256"]="0"*64;self.write()
  with patch("hole_shadow_bundle_audit.archived_four_modes",return_value=(200,self.archive)):
   r=audit(self.root,self.p)
  self.assertEqual(r["comparable"],0)
  self.assertEqual(r["excluded"][0]["reason"],"source_hash_mismatch")
 def test_duplicate_race_rejected(self):
  self.p.write_text(json.dumps({"status":"research_only_after_confirmed_push","records":[self.record,self.record]}))
  with self.assertRaises(ValueError):audit(self.root,self.p)
 def test_no_file_fails_closed(self):
  self.assertEqual(audit(self.root,self.p)["status"],"missing_shadow")
if __name__=="__main__":unittest.main()
