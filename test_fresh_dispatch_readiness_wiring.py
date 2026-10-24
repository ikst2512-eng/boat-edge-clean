"""Prevent external dispatch from bypassing formal readiness verification."""
from pathlib import Path

def check():
    workflow=Path(".github/workflows/fresh-dispatch-publish.yml").read_text()
    sender=Path("fresh_dispatch_sender.py").read_text()
    assert "run: python fresh_formal_source_preflight.py" in workflow
    assert workflow.index("run: python fresh_formal_source_preflight.py") < workflow.index("run: python fresh_dispatch_ingest.py")
    assert "source_check=check_remote" in sender
    assert 'status.get("ready") is not True' in sender
    assert "git push origin HEAD:main" in workflow
    print("Both dispatch sender and receiver require upstream formal readiness")

if __name__=="__main__":
    check()
