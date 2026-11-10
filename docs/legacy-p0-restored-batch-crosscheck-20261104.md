# P0 independent-restoration batch acceptance: fail-closed verifier (2026-11-04 JST)

**Scope:** Offline/local *restore-verification* tooling only, with no newly downloaded or externally backed up P0 original bytes. The historic source repositories, current prediction data, odds/results, CI, Pages and active workflows were not changed.

## What was actually checked

Building on the `legacy_original_preserver_guarded_v2_20261104.py` batch identity, the **new** `verify_p0_independent_restore_20261104.py` compares an originally captured batch with a *separately supplied restored directory*:

- Recomputes a SHA256 `plan_fingerprint` from the exact pinned original Git tree, ordered race identifiers, file paths and expected Git blob SHA1 values, then rejects any original/restored `batch_identity.json` that does not match.
- Independently reads both `local_readback_manifest.json` files and requires COMPLETE state, the same plan SHA256, number of races and source files, and an individual COMPLETE attempt receipt with exactly the planned file-path set.
- Independently recomputes the Git blob SHA1 and regular-file content SHA256 for **every file on both sides**, compares the SHA/byte-length evidence in the attempt receipts, and requires original vs restored checksums to match.
- Rejects same source/destination directory, missing or mutated originals, symlinks, altered/foreign batch fingerprint, duplicate/missing receipt entries, fake incomplete manifest, and corrupted declared SHA.
- Explicitly returns `independent_offsite_custody_verified=false` even on a successful local comparison. A provider upload/download attestation remains a **separate** externally verified requirement; copying a local folder does NOT prove external custody.

**Regression tests:** 10/10 newly added restoration tests PASS, plus the 15/15 prior guarded-preserver tests PASS (**25/25** total). The actual pinned P0 master matrix DRY_RUN for 25 races selected 118 source files, **writes=0**. This is a **simulated/local restore test, not external P0 source preservation**.

## Operator deliverable

`boat_edge_p0_independent_restore_verifier_20261104.zip`, 13,575 bytes, SHA256 `9eed75024267295dcab6726fd5688a7a0c9d8ca641330aa4f040a23e4857bb8b`. Contains 6 files: the new read-only verifier, its 10 tests, previous guarded preserver and hardened helper, the prior 15 tests, and README. ZIP integrity test PASS; contains **zero historical source bytes**.

**No new P0 originals retrieved, no new external source upload, no retirement authorization. P0 indexed original files remain 5,578 with the full 1,125-race forecast cohort not independently preserved. DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**