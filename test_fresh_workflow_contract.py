"""Check the snapshot witness and downstream feed handoff invariants."""
from pathlib import Path

def check():
    witness=Path(".github/workflows/fresh-snapshot-witness.yml").read_text()
    feed=Path(".github/workflows/fresh-witnessed-feed.yml").read_text()
    assert "paths:" in witness and "'fresh_snapshots/**'" in witness
    assert "workflow_dispatch:" not in witness
    assert "--diff-filter=A" in witness
    assert "len(paths)!=1 or paths!=added" in witness
    assert 'r"[0-9]{12}[.]json"' in witness
    assert "workflow_run:" in feed
    assert "github.event.workflow_run.conclusion == 'success'" in feed
    assert "github.event.workflow_run.head_branch == 'main'" in feed
    assert "fresh_feed_autopublish.py" in feed
    print("Witness and autopublish workflow contract passed")

if __name__=="__main__":
    check()
