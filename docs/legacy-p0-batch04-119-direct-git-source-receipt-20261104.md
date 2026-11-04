# P0 batch 04: 119 of 119 indexed source Git blobs verified (2026-11-04 JST)

**Legacy immutable source:** `ikst2512-eng/boat-edge` commit `f38204105a979aa6ef5293d1b9cad854056faadd`.

All 119 indexed historical JSON paths in exact frozen `batches/p0_batch_04_of_45.csv` were **directly read using authenticated GitHub `fetch_file`**, and returned Git blob identifiers were reconciled against the pinned CSV. Breakdown: **25 prediction snapshots, 25 audits, 24 histories, 20 odds, 25 results = 119**, all Git blob SHA1 MATCH.

The batch has **6 unindexed categories**: 5 odds files and 1 history. The unindexed history is `20261008-14-05` (Naruto 5R) and its separately fetched result source reports `status=trifecta_not_established`, consistent with the previous retirement-gate explanation; the other 24 returned results are confirmed. All 20 retrieved odds objects had 120 trifecta combinations. No unindexed original was invented.

The independent local batch04 checker `verify_p0_batch04_20261104.py` compared the GitHub-returned SHA1 strings to the actual frozen plan. A first manual transcription of one odds SHA was 39 instead of 40 characters, so this one path was **re-fetched directly from GitHub**, the full 40-char SHA was restored, and all 119 rows were compared again. **119 MATCH, 6 NOT_INDEXED, 0 discrepancy**.

Evidence CSV: `boat_edge_p0_batch04_119_git_blob_receipt_20261104.csv`, SHA256 `84dbd319e2bd405ac5dbbd9c30aa0b35b8fc4f65b3058504742032a5151ece02`. Reproducibility package `boat_edge_p0_batch04_direct_git_verification_20261104.zip` SHA256 `8ffc1cc79dbeb9aa746b3ac69848772630c3fd309caa94177db027dfaa28cccc`; script, receipt and summary, **no original source JSON files**.

**Cumulative** first four P0 batches: `118+115+117+119 = 469` indexed sources / **100 distinct historical races** Git-source SHA matches. These are **GitHub reported** blob identifiers, not an independent archive or restored bytes. The previously verified external P0 custody still comprises only one Kiryu 5R odds JSON, and the independent 412 result originals belong to P1/P2 with P0=0. Independent 5,578-source custody and restore remains unverified. No production or historical source edits and no unsafe connector-to-Drive transfer attempted.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED**; PR #1559 stays Draft and unmerged.