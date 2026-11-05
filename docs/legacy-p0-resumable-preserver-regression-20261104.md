# P0 recovery restart-safe preserver: 10/10 regression tests (2026-11-04 JST)

**Scope: operator-side read-only source recovery.** Existing old-site code, Actions, deployment, prediction/original source documents, odds, results and CLEAN UI remain unchanged.

## Detected regression hazard in previous standalone tool

The prior offline `legacy_original_preserver_hardened_20261104.py` correctly rejects overwrites and destination symlinks. However, on any partial fetch failure it still writes `local_readback_manifest.json`, and then rejects the same directory on restart. Thus recoverable partial source files could not be resumed cleanly in the same operator folder. A finalized marker was also indistinguishable from a fully verified batch. **This is a tooling acceptance defect, not evidence of loss of original source data.**

## Additive, offline-tested replacement

`legacy_original_preserver_resumable_20261104.py` is an operator-side replacement, leaving prior scripts intact:

- Each iteration validates already saved originals against the pinned Git blob SHA1 **before further network activity**. A mismatch or symlink is rejected rather than overwritten.
- Missing originals are downloaded, Git SHA1 checked before exclusive creation, then locally read back and SHA256 recorded.
- An `attempt_history/attempt-NNNN.json` receipt records each attempt, including partial failures. The **final** `local_readback_manifest.json` is written only after **all** source references in a batch verify successfully, and then replay checks every source file.
- Re-running an incomplete batch reuses **only verified** originals; it downloads missing sources. A fully complete batch refuses further write attempts.
- Source path traversal, duplicate paths/races, invalid SHA, target/ancestor symlinks, and unsafe output paths fail closed. Default mode is DRY_RUN with **zero disk writes**.
- Concurrent malicious directory modifications remain a residual TOCTOU risk; run on a secured dedicated operator filesystem with no other writers. Exclusive lock protects a particular attempt receipt, not arbitrary concurrent workflows. The final local manifest **explicitly declares external backup verification false**.

**Independent offline tests: 10/10 PASS**, including an induced network interruption, an actual retry that fetched only the missing source, malformed paths, forged fetched bytes, existing-file tamper, symlink, and erroneous finished-batch reexecution. Actual P0 matrix `--limit 25` DRY_RUN identified **25 races / 118 source references / writes=0**.

Self-contained user artifact: `boat_edge_p0_resumable_protection_20261104.zip`, ZIP SHA256 `8f57a4f3ed4835da81afc61042a60e84580b9467979a63084ce81e5384d5fbd3`, includes script, original hardened helper, unit tests and README; **contains zero original source bytes**. This ZIP is intentionally not a replacement for the 45-batch manifest nor an external original-file backup.

No P0 originals were fetched by this dry-run/test; no Google Drive original transfer was attempted. **P0 independent storage / full byte restore NOT COMPLETE**, old 412 result archive covers P1/P2 only. **DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED**. Keep PR Draft until branch-main divergence and dependencies are reconciled.