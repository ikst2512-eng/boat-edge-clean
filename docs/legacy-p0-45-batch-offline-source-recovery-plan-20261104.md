# P0 immutable-original source recovery: 45-batch operator plan (2026-11-04 JST)

This document is **not a completed source backup** and makes no claim of source bytes transferred. It accompanies an offline verified operator plan.

**Scope: 1,125 P0 race IDs; 5,578 distinct indexed originals** at fixed legacy tree `f38204105a979aa6ef5293d1b9cad854056faadd`:
- 1,125 prediction snapshots
- 1,125 audit receipts
- 1,124 result-gated history files
- 1,079 odds-sidecar files
- 1,125 result files

The 46 unindexed odds and one unindexed history are **not fabricated**. Earlier archived 412 result originals cover **P0=0, P1=61, P2=351**, and therefore do not reduce any P0 file counts. Previously validated Kiryu 5R odds original is the only P0 original independently uploaded and read back as a standalone Drive ZIP.

## New deterministic batch manifest, local-only validation

`boat_edge_p0_45_batch_preservation_plan_20261104.zip` SHA256 `f4eb61a45e641e88129d1b3b925a5806f40b02cc68ac067c63c3ed410e4c1b5e`. Includes **45 CSV batches** of exactly **25 race IDs each**, `batch_plan_manifest.json` containing per-batch row counts, original-source counts and CSV SHA256, and a readme. The source 4,143-race matrix is left unchanged. Independent offline tests confirmed:
- `45 × 25 = 1,125` unique P0 race IDs with no duplication or omission.
- The 45 batches partition all **5,578** indexed file references.
- All 45 CSVs parse consistently and ZIP CRC read test passes.
- The package contains **zero** original prediction/odds/result bytes. It is a *manifest / batch plan*, not independent preservation.

The existing tested read-only `legacy_original_preserver.py` (already shipped in `boat_edge_original_preservation_toolkit_20261104.zip`) can be executed by an authorized network-enabled operator on each 25-row batch with `--limit 0 --execute`, using a unique destination per batch. It validates source Git blob hashes and independently hashes locally written bytes; it does **not** establish offsite preservation on its own. Run `verify_p0_full_originals_20261104.py` against a carefully consolidated local mirror after all batches, and require an independent off-service copy **and successful restored SHA256 validation** before accepting retirement. Never use an unverified / incomplete destination as proof of full backup.

The current chat/container execution environment could not resolve `raw.githubusercontent.com` or `api.github.com` DNS; the prior direct GitHub-to-Google-Drive forecast byte transfer was blocked by safety checks. **Do not bypass the restriction or invent successful new source retrieval.** This batch plan is a safe authorized-operator handoff, not a workaround or covert transfer.

**No source edits, no running of old-site jobs, no workflow disabling, no merging divergent PR, no deletion. DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
