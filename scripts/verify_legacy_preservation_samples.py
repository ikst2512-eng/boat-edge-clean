"""Verify byte-identical archival copies of sampled legacy prediction snapshots.

This does not prove first Git-add timing, pre-deadline eligibility or complete preservation.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "legacy_preservation/samples/manifest.json"


def verify(root=ROOT):
    manifest = json.loads((root / "legacy_preservation/samples/manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_repository"] == "ikst2512-eng/boat-edge"
    records = manifest["records"]
    assert len(records) == 3, "unexpected preservation sample count"
    seen = set()
    for row in records:
        rel = row["archive_path"]
        assert rel.startswith("legacy_preservation/samples/") and ".." not in Path(rel).parts
        assert rel not in seen
        seen.add(rel)
        source = row["original_path"]
        assert source == "data/site_prediction_snapshots/" + Path(rel).name
        raw = (root / rel).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()
        assert actual == row["source_blob_sha"], f"legacy source blob mismatch: {rel}"
        body = json.loads(raw)
        assert body["race_key"] == row["race_key"] == Path(rel).stem
    return len(seen)


if __name__ == "__main__":
    print(f"LEGACY_PRESERVATION_BLOB_MATCH={verify()}")
