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
            if "/contents/" in url: return {"type":"file"}
            return {"state":"active","path":".github/workflows/research-pair-capture-manual.yml"}
        x=preflight(fetch)
        self.assertTrue(x["registered_on_default"])
        self.assertTrue(x["dispatch_ready"])
    def test_registered_but_disabled_not_ready(self):
        def fetch(url):
            if url.endswith("/repos/ikst2512-eng/boat-edge-clean"):
                return {"default_branch":"main"}
            if "/contents/" in url: return {"type":"file"}
            return {"state":"disabled_manually","path":".github/workflows/research-pair-capture-manual.yml"}
        state=preflight(fetch)
        self.assertFalse(state["dispatch_ready"])
    def test_file_exists_but_actions_registration_missing(self):
        def fetch(url):
            if url.endswith("/repos/ikst2512-eng/boat-edge-clean"):
                return {"default_branch":"main"}
            if "/contents/" in url: return {"type":"file"}
            raise HTTPError(url,404,"Not Found",None,None)
        self.assertFalse(preflight(fetch)["dispatch_ready"])

if __name__=="__main__":
    unittest.main()
