import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_shadow_batch_audit import batch

class BatchTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name);(self.root/"captureA").mkdir()
  (self.root/"captureB").mkdir()
  for x in ("captureA","captureB"):
   (self.root/x/"hole-shadow.json").write_text("{}")
 def row(self,code,winner):
  return {"race_code":code,"flags":{key:{f"top{k}":bool(winner==key) for k in (3,5,10)}
                                    for key in ("baseline","shadow","shadow_bundle2")}}
 def test_aggregate_without_double_count(self):
  a={"status":"retrospective_shadow_comparison","rows":[self.row("202611030101","shadow_bundle2")],"excluded":[]}
  b={"status":"retrospective_shadow_comparison","rows":[self.row("202611030102","baseline")],"excluded":[]}
  with patch("hole_shadow_batch_audit.audit",side_effect=[a,b]):
   r=batch(self.root,self.root)
  self.assertEqual(r["compared"],2)
  self.assertEqual(r["delta"]["shadow_bundle2"]["top10"]["net"],0)
  self.assertFalse(r["formal"])
 def test_duplicate_fails_closed(self):
  a={"status":"retrospective_shadow_comparison","rows":[self.row("202611030101","baseline")],"excluded":[]}
  with patch("hole_shadow_batch_audit.audit",side_effect=[a,a]):
   with self.assertRaises(ValueError):batch(self.root,self.root)
 def test_no_artifacts_not_success(self):
  with tempfile.TemporaryDirectory() as p:
   self.assertEqual(batch(self.root,p)["status"],"no_capture_artifacts")
if __name__=="__main__":unittest.main()
