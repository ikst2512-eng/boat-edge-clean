# 2026-11-09 hole-pair same-race source blob drift — NONFORMAL, research Draft #1685

## What changed and why

A same-day original forecast **race ID** can persist across two immutable main commits even if the forecast **contents** were replaced. The preceding `research/hole_pair_snapshot_id_drift_audit.py` correctly reports added and missing race IDs but intentionally cannot prove equal-ID source-byte identity. The new **read-only** `research/hole_pair_source_blob_drift_audit.py` closes this specific diagnostic gap without changing the original frozen tickets, selector, official T−12 collection, or scheduled research.

For an existing **Nov 9+ nonformal candidate manifest**, it checks:

1. Original and later exact 40-character immutable Git main commit SHAs; the later commit **must be proven a descendant** of the first with `git merge-base --is-ancestor`, or audit fails.
2. Both immutable Git tree inventories, reading **only Git path/blob metadata under `four_mode_forecasts/`**. Never open forecast contents or confirmed results. Reject malformed, duplicate, symlink/submodule, out-of-day or unsafe same-day source entries.
3. Original source race IDs against the manifest's original complete snapshot roster. For every frozen candidate, compare its saved `source_git_blob_sha1` to the **actual original Git tree blob ID**, not a claimed later blob.
4. Same race IDs with different original-vs-later blob SHAs: report `same_race_source_blob_drift_quarantine_and_review`, with exact race IDs and both Git blob IDs. Added and missing race IDs retain the prior independent ID-drift report.

This is a **diagnostic**, not a copy/rewrite of a candidate and not evidence that a source forecast was first remotely accepted before its cutoff. A later same-ID forecast file change must not silently replace the original in a 300+300 ledger, nor justify choosing bets from settled results. Even if all IDs/blob SHAs match, whole-day race universe, raw source SHA-256 authentication, signed independent first candidate receipt, official six-boat beforeinfo/exhibition plus all 120 original odds and official T−12 chronology remain **unverified**.

## Run manually against existing unverified research manifest (when available)

From a research checkout containing both Git commit objects:

```bash
python research/hole_pair_source_blob_drift_audit.py \
  --manifest /path/to/original/research_candidate_freeze.json \
  --later-main-sha <exact_40_character_descendant_main_commit_sha>
```

The script never creates, republishes, or reselects any frozen candidate; reads no outcomes; and does not call GitHub/Cloudflare/Render APIs. All success and drift reports explicitly carry `formal=false`, `first_remote_receipt_verified=false`, `pilot_formally_eligible=0`, `confirmation_formally_eligible=0`, `production_promotion_allowed=false`. It is limited to source-file Git blob *identity*; Git SHA1 matches are not independent first-receipt timestamps or attestations. No Git clone/manifest for a genuinely captured Nov9+ cohort was created by this change.

## CI and fix chronology

- New `research/test_hole_pair_source_blob_drift_audit.py`: **14 synthetic negative/positive tests** for first Git tree census, frozen original source blob claim, changed same-race IDs, added/missing IDs, fake formal claims, non-descendant commits, invalid tree paths and failed Git commands.
- The initial [Actions #42616334913](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42616334913) **failed** because the test mock read `git ls-tree` commit argument at index 2 (`-r`) instead of index 3. The implementation did not change; only the mock index was corrected.
- Exact code-head [Actions #42616453081](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42616453081) **SUCCESS** on commit `7c8927bccf2176ab00b094386e349583e514de9d`: new **14/14**, existing research checks succeeded; real candidate freeze and candidate artifact upload **SKIPPED** under PR event. The only produced artifact was the existing readiness artifact, not a new candidate or first receipt.

## Strict holding boundary

Draft #1685 remains unmerged; Draft #1702 is the **preferred manually reviewed gateway** over competing #1701, but remains unmerged and inactive. Its pinned source commit `464d1641a5c7b981248ab17ba5bdc42b7bfa698b` was **not repinned** to this new research audit. No gateway/D1 transport, live Cloudflare resource, full-day scheduler, production predictor, model, UI, Render, official collector or `main` change. Pilot **0/300**, confirmation **0/300** formally eligible. No claim of higher real prediction accuracy or formal prospective evaluation.
