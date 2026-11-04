# Correction: 412 independently archived result originals cover P1/P2, not P0 — 2026-11-04

**Important scope clarification for Issue #708 and Draft PR #1559.**

An independent read-only reconciliation compares the exact **412 result JSON original bytes** recovered from GitHub Actions run `40936953310`, artifact `12924304439` (ZIP SHA256 `9460f06cc712a87756ef4f54feb0612d63c812562b6486be12491e48be10e216`), with each row of the pinned crosswalk `boat_edge_legacy_retention_race_matrix_20261104.csv`.

For every one of the 412 files, Git blob SHA1 independently reconstructed from recovered TAR bytes equals the archived manifest AND the pinned crosswalk `result_blob_sha`; calculated source SHA256 equals archived manifest SHA256. **412/412 PASS**, 0 byte conflicts.

| Cohort | Recovered result originals in this 412-file archive |
| --- | ---: |
| P0 — legacy-exclusive prediction | **0** |
| P1 — shared race with prediction provenance | **61** |
| P2 — inputs/results only | **351** |
| Total | **412** |

Therefore, **the successful independent Google Drive archive/readback of 412 old RESULT originals does not preserve any of the 1,125 P0 RESULT files**. The result-only archive also does NOT include original P1 forecast snapshots. This materially narrows previously generalized language describing 'legacy results backup' and its relevance to P0 retirement.

For repeatability, local `boat_edge_412_cohort_correction_20261104.zip` (SHA256 `fed0780a10aed76eafeec06925eecdabfa6315a4fa327400b2413cab8beccfe5`) contains read-only `reconcile_legacy_412_cohorts.py`, 412-row detailed receipt CSV and summary JSON. It expects the original 412 Actions ZIP and the original crosswalk matrix as separately supplied inputs; it does not copy or expose historical original bytes. A local run returned **P1=61, P2=351, P0=0** with 412/412 source SHA and Git blob matching.

P0 indexed sources remain 5,578 across 1,125 races, and are NOT backed up just because these 412 other results were archived. The previously verified single Kiryu 5R original odds is one P0 source (not one P0 result), and is separately retained in Drive. P0 forecast original-byte complete-backup and offsite restore remain unverified.

**Do not decommission, delete, rewrite or stop any legacy writer, workflow, Pages source, or model on the strength of the 412-result archive. DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
