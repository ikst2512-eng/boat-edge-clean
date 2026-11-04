# P0 original-file preserver: batch identity and single-writer protection — 2026-11-04 JST

**Scope:** operator-side recovery code review only. Original source bytes were **not fetched**, uploaded or modified. The old site, CI, Actions, Pages, predictions, odds, results and other teams' code were untouched.

## Follow-up regression gap

The previous `legacy_original_preserver_resumable_20261104.py` correctly resumed a partially downloaded *same* batch, but did **not persist the selected batch identity**. Changing source matrix or selecting other 25 races while reusing a directory could lead to cross-batch provenance ambiguity. In addition, per-attempt `attempt-NNNN.lock` reservations did not serialize the full source verification/fetch/finalization process across concurrent invocations.

## Additive V2 guarded operator utility

New standalone `legacy_original_preserver_guarded_v2_20261104.py` (does not alter earlier scripts):

- Compute a deterministic SHA256 fingerprint of **the complete ordered set of race codes, pinned tree, paths and Git blob hashes**, and persist `batch_identity.json` on first execution. Every subsequent run must match the identity, count and race number or refuse operation.
- Reject unbound existing nonempty destinations rather than silently relabeling prior data; **use a newly created empty destination for each batch**. Existing partial directories from the old utility require separately reviewed migration, not automatic relabeling.
- Enforce a root-level exclusive `.source-preserver-active.lock` from initial batch acceptance through completion. Another process trying the same destination fails before download. A stale lock after abnormal termination requires **manual investigation**, not blind removal.
- Bind the same `plan_sha256` into the final `local_readback_manifest.json`; continuing without matching fingerprints is forbidden.
- Retain checks for SHA mismatch, symlinks, source path safety, local readback and resumable verified-file reuse. Source ZIP includes the prior hardened helper but no historic original files.

**Verification:** 15/15 tests PASS, including five new tests for changed-batch reuse, concurrent lock, final fingerprint, identity symlink, and same-plan resume. An actual P0 matrix read-only DRY_RUN for 25 races identified **118 indexed source paths and zero writes**.

**Delivered package:** `boat_edge_p0_guarded_batch_identity_v2_20261104.zip`, 10,107 bytes, SHA256 `b0c7fe460995cafd00ac0173ee03e2cbeca6fbdb28561c8906aa78be5651cf48`, ZIP CRC PASS; includes code, 15 tests and operator README only. **No 1,125 P0 forecast originals or 5,578 indexed source bytes are included.** No live source fetch or external-offsite backup is claimed.

Residual protection boundary: this utility is not race-free against malicious local filesystem mutation by untrusted concurrent processes; use a protected single-writer operator filesystem and independent offsite restore verification. Old-site retirement remains blocked.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**