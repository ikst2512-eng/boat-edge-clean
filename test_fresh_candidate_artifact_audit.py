from fresh_candidate_artifact_audit import check_artifact

def check():
    receipt={"schema":"fresh-prospective-receipt-v1","independent_github_arrival_verified":False,
             "workflow_run_id":123,"workflow_attempt":1,"deadline_at":"2026-10-25T03:00:00+00:00",
             "race_code":"202610251201"}
    run={"id":123,"run_attempt":1,"event":"repository_dispatch","conclusion":"success",
         "head_branch":"main","path":".github/workflows/fresh-prospective-capture.yml",
         "created_at":"2026-10-25T02:40:00Z"}
    art={"name":"prospective-v5-123","id":44,"expired":False,"size_in_bytes":1000,
         "digest":"sha256:"+"a"*64,"created_at":"2026-10-25T02:45:00Z",
         "workflow_run":{"id":123}}
    assert check_artifact(receipt,run,{"artifacts":[art]})["artifact_created_before_cutoff"]
    assert not check_artifact(receipt,run,{"artifacts":[art]})["candidate_bytes_independently_verified"]
    def reject(**updates):
        try:check_artifact(receipt,run,{"artifacts":[{**art,**updates}]})
        except ValueError:return
        raise AssertionError("untrusted artifact accepted")
    reject(created_at="2026-10-25T02:48:00Z")
    reject(workflow_run={"id":124})
    reject(expired=True)
    reject(name="other")
    print("GitHub artifact creation cutoff regression PASS")
if __name__=="__main__":check()
