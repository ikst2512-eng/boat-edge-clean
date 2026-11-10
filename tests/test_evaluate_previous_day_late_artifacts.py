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
        forwarded_headers={header.lower() for header in redirected.headers}
        self.assertNotIn("authorization",forwarded_headers)
        self.assertNotIn("x-github-api-version",forwarded_headers)
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

    @staticmethod
    def source_run(run_id, event="schedule", branch="main", repo="example/repo"):
        return {"id":run_id,"event":event,"head_branch":branch,
                "head_repository":{"full_name":repo},
                "created_at":"2026-10-31T02:00:00Z"}

    def test_scan_continues_past_five_pages_without_global_artifact_cap(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if "/actions/workflows/" in url:
                page=int(__import__("urllib.parse",fromlist=["parse_qs"]).parse_qs(__import__("urllib.parse",fromlist=["urlsplit"]).urlsplit(url).query)["page"][0])
                runs=[] if page==6 else [self.source_run(page*100+i,event="pull_request") for i in range(100)]
                return json.dumps({"workflow_runs":runs}).encode()
            self.fail("PR runs must not be treated as saved research candidates")
        with tempfile.TemporaryDirectory() as tmp:
            report=retrieve("20261031",tmp,"example/repo","mock",fetch)
            self.assertTrue(report["artifact_scan_complete"])
            self.assertEqual(report["coverage_status"],"no_prior_day_candidate_found")
            self.assertEqual(report["workflow_run_pages_scanned"],6)
            self.assertEqual(report["trusted_source_runs"],0)
            self.assertEqual(len(calls),6)
            self.assertTrue(all("research-live-preview-evidence.yml/runs?" in url for url in calls))

    def test_duplicate_immutable_candidate_still_counts_each_source_artifact(self):
        day="20261031"
        code="202610310708"
        blob=archive({"late_research_candidates/"+day+"/"+code+".json":{
            "race_code":code,"status":"research_candidate_unvalidated","research_only":True}})
        def fetch(url):
            if "/actions/workflows/" in url:
                return json.dumps({"workflow_runs":[self.source_run(1),self.source_run(2)]}).encode()
            if "/actions/runs/" in url:
                run_id=int(url.split("/actions/runs/")[1].split("/")[0])
                return json.dumps({"artifacts":[{
                    "id":10+run_id,"name":f"independent-late-preview-{run_id}",
                    "expired":False,"archive_download_url":
                    f"https://api.github.com/repos/example/repo/actions/artifacts/{10+run_id}/zip"}]}).encode()
            return blob
        with tempfile.TemporaryDirectory() as tmp:
            report=retrieve(day,tmp,"example/repo","mock",fetch)
            self.assertEqual(report["imported_immutable_candidates"],1)
            self.assertEqual(report["artifacts_with_imported_candidates"],2)
            self.assertEqual(report["trusted_source_runs"],2)

    def test_recovers_eligible_artifact_without_inventing_data(self):
        day="20261031"
        code="202610310708"
        blob=archive({"late_research_candidates/"+day+"/"+code+".json":{
            "race_code":code,"status":"research_candidate_unvalidated","research_only":True}})
        def fetch(url):
            if "/actions/workflows/" in url:
                self.assertIn("created=",url)
                return json.dumps({"workflow_runs":[self.source_run(123)]}).encode()
            if "/actions/runs/" in url:
                return json.dumps({"artifacts":[{
                    "id":3,"name":"independent-late-preview-123",
                    "expired":False,"archive_download_url":
                    "https://api.github.com/repos/example/repo/actions/artifacts/3/zip"}]}).encode()
            return blob
        with tempfile.TemporaryDirectory() as tmp:
            result=retrieve(day,tmp,"example/repo","mock",fetch)
            self.assertEqual(result["imported_immutable_candidates"],1)
            self.assertEqual(result["artifacts_with_imported_candidates"],1)
            self.assertEqual(result["coverage_status"],"candidate_found")

    def test_expired_artifact_never_certified_as_no_candidates(self):
        def fetch(url):
            if "/actions/workflows/" in url:
                return json.dumps({"workflow_runs":[self.source_run(4)]}).encode()
            if "/actions/runs/" in url:
                return json.dumps({"artifacts":[{
                    "id":5,"name":"independent-late-preview-4","expired":True}]}).encode()
            self.fail("Expired artifact must not be fetched")
        with tempfile.TemporaryDirectory() as tmp:
            report=retrieve("20261031",tmp,"example/repo","mock",fetch)
            self.assertFalse(report["artifact_scan_complete"])
            self.assertEqual(report["coverage_status"],"expired_source_artifacts_unverifiable")

    def test_incomplete_source_run_pagination_does_not_claim_zero(self):
        def fetch(url):
            if "/actions/workflows/" in url:
                return json.dumps({"workflow_runs":[self.source_run(100+i,event="pull_request")
                    for i in range(100)]}).encode()
            self.fail("Excluded PR must never query artifacts")
        with tempfile.TemporaryDirectory() as tmp:
            report=retrieve("20261031",tmp,"example/repo","mock",fetch)
            self.assertFalse(report["artifact_scan_complete"])
            self.assertEqual(report["coverage_status"],"incomplete_source_workflow_scan")
            self.assertEqual(report["workflow_run_pages_scanned"],20)

    def test_untrusted_artifact_metadata_cannot_receive_github_token(self):
        def fetch(url):
            if "/actions/workflows/" in url:
                return json.dumps({"workflow_runs":[self.source_run(55)]}).encode()
            if "/actions/runs/" in url:
                return json.dumps({"artifacts":[{
                    "id":56,"name":"independent-late-preview-55",
                    "expired":False,"archive_download_url":"https://other.invalid/leak"}]}).encode()
            self.fail("Untrusted artifact URL was fetched")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"untrusted_artifact_archive_url"):
                retrieve("20261031",tmp,"example/repo","mock-token",fetch)


if __name__=="__main__":
    unittest.main()
