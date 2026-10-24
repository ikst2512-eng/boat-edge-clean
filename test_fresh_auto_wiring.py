"""Catch accidental removal of the Fresh witness-to-site workflow chain."""
from pathlib import Path

def check():
    witness=Path(".github/workflows/fresh-snapshot-witness.yml").read_text()
    finalize=Path(".github/workflows/fresh-witness-finalize.yml").read_text()
    dispatch=Path(".github/workflows/fresh-dispatch-publish.yml").read_text()
    assert "name: Fresh snapshot arrival witness" in witness
    assert "branches: [main]" in witness
    assert "Fresh snapshot arrival witness" in finalize
    assert "workflow_run:" in finalize and "types: [completed]" in finalize
    assert "head_repository.full_name == github.repository" in finalize
    assert "head_branch == 'main'" in finalize
    assert "fresh_auto_finalize.py" in finalize
    assert "git push origin HEAD:main" in finalize
    assert "secrets.FRESH_PUSH_TOKEN" in dispatch
    assert "fresh_dispatch_ingest.py" in dispatch
    print("Fresh external dispatch -> witness -> API feed workflow wiring passed")
if __name__=="__main__":check()
