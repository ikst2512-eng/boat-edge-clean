from fresh_candidate_arrival_audit import check

def run():
    receipt={"schema":"fresh-prospective-receipt-v1",
             "independent_github_arrival_verified":False,
             "workflow_run_id":123,"workflow_attempt":1,
             "deadline_at":"2026-10-25T03:00:00+00:00","race_code":"202610251201"}
    proof={"id":123,"run_attempt":1,"event":"repository_dispatch","conclusion":"success",
           "head_branch":"main","path":".github/workflows/fresh-prospective-capture.yml@refs/heads/main",
           "created_at":"2026-10-25T02:40:00Z"}
    result=check(receipt,proof)
    assert result["formal_approved"] is False
    assert result["github_workflow_started_before_cutoff"] is True
    assert result["candidate_uploaded_before_cutoff_verified"] is False
    def reject(**changes):
        try:check(receipt,{**proof,**changes})
        except ValueError:return
        raise AssertionError("untrusted run accepted")
    reject(created_at="2026-10-25T02:49:00Z")
    reject(event="workflow_dispatch")
    reject(conclusion="failure")
    reject(id=124)
    reject(path=".github/workflows/fresh-snapshot-witness.yml")
    print("Candidate independent GitHub arrival audit PASS")

if __name__=="__main__":run()
