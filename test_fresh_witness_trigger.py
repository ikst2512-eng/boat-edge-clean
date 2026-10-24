"""Guard against reintroducing the GitHub Actions GITHUB_TOKEN witness deadlock."""
from pathlib import Path

def check():
    publication=Path(".github/workflows/fresh-v5-immutable-publication.yml").read_text()
    witness=Path(".github/workflows/fresh-snapshot-witness.yml").read_text()
    assert "secrets.FRESH_PUSH_TOKEN" in publication
    assert "Missing FRESH_PUSH_TOKEN" in publication
    assert "token: ${{ secrets.FRESH_PUSH_TOKEN }}" in publication
    assert "git push origin HEAD:main" in publication
    assert "fresh_snapshots/**" in witness
    assert "branches: [main]" in witness
    assert "      - 'fresh_snapshots/**'" in witness
    print("Witness-trigger authentication guard passed")

if __name__=="__main__":
    check()
