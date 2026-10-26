import unittest
from urllib.error import HTTPError
from research_pair_dispatch_preflight import preflight

class DispatchPreflightTests(unittest.TestCase):
    def test_absent_default_workflow_is_not_ready(self):
        def fetch(url):
            if url.endswith("/repos/ikst2512-eng/boat-edge-clean"):
                return {"default_branch":"main"}
            raise HTTPError(url,404,"Not Found",None,None)
        x=preflight(fetch)
        self.assertFalse(x["dispatch_ready"])
        self.assertFalse(x["registered_on_default"])
    def test_registered_workflow_requires_further_verification(self):
        def fetch(url):
            if url.endswith("/repos/ikst2512-eng/boat-edge-clean"):
                return {"default_branch":"main"}
            return {"type":"file"}
        x=preflight(fetch)
        self.assertTrue(x["registered_on_default"])
        self.assertIn("verify enabled",x["reason"])
if __name__=="__main__":
    unittest.main()
