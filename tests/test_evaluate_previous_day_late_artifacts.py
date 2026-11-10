import io, json, tempfile, unittest, zipfile, subprocess, sys
from urllib.request import Request
from pathlib import Path
from scripts.evaluate_previous_day_late_artifacts import extract_candidates, retrieve, _DiscardCrossHostAuth


def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w") as zipfile_out:
        for name,record in entries.items():
            zipfile_out.writestr(name,json.dumps(record))
    return stream.getvalue()


class PriorArtifactTest(unittest.TestCase):
    def test_recheck_cli_supports_delayed_result_window(self):
        run=subprocess.run([sys.executable,"-m","scripts.evaluate_previous_day_late_artifacts","--help"],
                           capture_output=True,text=True,check=True)
        self.assertIn("--days-ago",run.stdout)
        self.assertIn("{1,2,3}",run.stdout)

    def test_only_valid_late_candidates_are_imported_and_immutable(self):
        day="20261031"
        code="202610310708"
        record={"race_code":code,"status":"research_candidate_unvalidated",
                "research_only":True,"predictions":["1-2-3"]}
        blob=archive({"late_research_candidates/"+day+"/"+code+".json":record,
                      "research_snapshots/"+day+"/"+code+".json":record,
                      "late_research_candidates/20261030/202610300708.json":record,
                      "../evil.json":record})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(extract_candidates(blob,day,root),1)
            self.assertEqual(extract_candidates(blob,day,root),0)
            self.assertFalse((root/"evil.json").exists())
            path=root/day/(code+".json")
            self.assertEqual(json.loads(path.read_text())["race_code"],code)
            altered=archive({"late_research_candidates/"+day+"/"+code+".json":dict(record,predictions=["2-1-3"])})
            with self.assertRaisesRegex(ValueError,"conflicting"):
                extract_candidates(altered,day,root)
            self.assertEqual(json.loads(path.read_text())["predictions"],["1-2-3"])

    def test_cross_host_artifact_redirect_drops_bearer_credentials(self):
        handler=_DiscardCrossHostAuth()
        request=Request("https://api.github.com/repos/example/repo/actions/artifacts/3/zip",
                        headers={"Authorization":"Bearer SECRET","X-GitHub-Api-Version":"2022-11-28"})
        redirected=handler.redirect_request(request,None,302,"Found",{},
                "https://objects.githubusercontent.com/artifact/archive.zip?sig=opaque")
        self.assertIsNone(redirected.get_header("Authorization"))
        self.assertIsNone(redirected.get_header("X-GitHub-Api-Version"))
        self.assertEqual(redirected.full_url.split("?")[0],
                "https://objects.githubusercontent.com/artifact/archive.zip")
        same_origin=handler.redirect_request(request,None,302,"Found",{},
                "https://api.github.com/repos/example/repo/actions/artifacts/3/zip?redirect=1")
        self.assertEqual(same_origin.get_header("Authorization"),"Bearer SECRET")
        with self.assertRaisesRegex(ValueError,"insecure_github_artifact_redirect"):
            handler.redirect_request(request,None,302,"Found",{},
                    "http://objects.githubusercontent.com/artifact/archive.zip")

    def test_untrusted_artifact_metadata_cannot_receive_github_token(self):
        def fetch(url):
            if "page=1" in url:
                return json.dumps({"artifacts":[{"name":"independent-late-preview-1",
                     "expired":False,"archive_download_url":"https://other.invalid/leak"}]}).encode()
            self.fail("Untrusted artifact URL was fetched")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"untrusted_artifact_archive_url"):
                retrieve("20261031",tmp,"example/repo","mock-token",fetch)

    def test_scan_continues_past_five_pages(self):
        day="20261031"
        calls=[]
        def fetch(url):
            calls.append(url)
            if "page=6" in url:
                return json.dumps({"artifacts":[]}).encode()
            return json.dumps({"artifacts":[{"name":"irrelevant-"+str(i),
                "expired":False} for i in range(100)]}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            report=retrieve(day,tmp,"example/repo","mock",fetch)
            self.assertTrue(report["artifact_scan_complete"])
            self.assertEqual(report["coverage_status"],"no_prior_day_candidate_found")
            self.assertEqual(len(calls),6)

    def test_duplicate_immutable_candidate_still_counts_each_source_artifact(self):
        day="20261031"
        code="202610310708"
        blob=archive({"late_research_candidates/"+day+"/"+code+".json":{
            "race_code":code,"status":"research_candidate_unvalidated","research_only":True}})
        def fetch(url):
            if "page=1" in url:
                return json.dumps({"artifacts":[
                    {"name":"independent-late-preview-1","expired":False,"archive_download_url":"https://api.github.com/repos/example/repo/actions/artifacts/1/zip"},
                    {"name":"independent-late-preview-2","expired":False,"archive_download_url":"https://api.github.com/repos/example/repo/actions/artifacts/2/zip"}]}).encode()
            return blob
        with tempfile.TemporaryDirectory() as tmp:
            result=retrieve(day,tmp,"example/repo","mock",fetch)
            self.assertEqual(result["imported_immutable_candidates"],1)
            self.assertEqual(result["artifacts_with_imported_candidates"],2)

    def test_recovers_eligible_artifact_without_inventing_data(self):
        day="20261031"
        code="202610310708"
        blob=archive({"late_research_candidates/"+day+"/"+code+".json":{
            "race_code":code,"status":"research_candidate_unvalidated","research_only":True}})
        def fetch(url):
            if "page=1" in url:
                return json.dumps({"artifacts":[{"name":"independent-late-preview-123",
                     "expired":False,"archive_download_url":"https://api.github.com/repos/example/repo/actions/artifacts/3/zip"}]}).encode()
            return blob
        with tempfile.TemporaryDirectory() as tmp:
            result=retrieve(day,tmp,"example/repo","mock",fetch)
            self.assertEqual(result["imported_immutable_candidates"],1)
            self.assertEqual(result["artifacts_with_imported_candidates"],1)
            self.assertEqual(result["coverage_status"],"candidate_found")

if __name__=="__main__":
    unittest.main()
