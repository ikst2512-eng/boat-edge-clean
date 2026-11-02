import io
import json
import unittest
import zipfile
from hole_capture_artifact_inventory import inspect_capture,zip_shadow
class CaptureInventoryTests(unittest.TestCase):
 def test_frozen_bundle_count(self):
  x={"records":[{"status":"shadow_frozen_unverified","shadow_bundle2":["1-2-3"]},
                {"status":"past_deadline"},{"status":"shadow_frozen_unverified"}]}
  self.assertEqual(inspect_capture(x)["bundle2"],1)
  self.assertEqual(inspect_capture(x)["frozen"],2)
 def test_zip_shadow(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,"w") as f:
   f.writestr("four-mode-evidence/hole-shadow.json",
      json.dumps({"status":"research_only_after_confirmed_push","records":[
       {"status":"shadow_frozen_unverified","shadow_bundle2":["1-2-3"]}]}))
  self.assertEqual(zip_shadow(buf.getvalue())["bundle2"],1)
 def test_missing_does_not_look_successful(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,"w") as f:f.writestr("foo.txt","none")
  self.assertEqual(zip_shadow(buf.getvalue())["status"],"no_hole_shadow_in_artifact")
if __name__=="__main__":unittest.main()
