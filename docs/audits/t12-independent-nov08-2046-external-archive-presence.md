# 2026-11-08 ~20:46 JST — Independent persisted official-three-source archive presence audit

This is a **read-only audit** within Draft PR #1694, not collection recovery, formal certification, or main deployment.

## Exactly checked

The existing official three-original remote durability channel is GitHub branch `research-t12-external-evidence`, prefix `external_three_t12/`. From the [actual GitHub API](https://api.github.com/repos/ikst2512-eng/boat-edge-clean/contents/external_three_t12?ref=d0ed89f146dff117021c2bc042b20259d6715515), this branch's checked commit `d0ed89f146dff117021c2bc042b20259d6715515` has only directory `external_three_t12/20261103`; **`external_three_t12/20261108` does not exist** at this immutable commit. Therefore the number of **Nov 8 saved race directories in this specific official-three-original Git branch is zero**. This observation is *not* an exhaustive denial of temporary Actions ZIP artifacts or other research branches; the independent [14:15 Edogawa9 two-original Action archive](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) remains real.

The branch has a historical Nov 3 directory, so the path and branch naming are validated, rather than mistaking a nonexistent branch for an empty day. This proves a Nov 8 **durable remote official trio evidence gap in this channel**, not an underlying boatrace.jp HTTP 404 and not a reason to make any prior forecast formally eligible.

## New automated audit

- New `scripts/audit_t12_external_archive_presence.py` verifies exact GitHub branch SHA, pins all subsequent directory reads to that immutable commit, validates YYYYMMDD and race-directory identity, and returns separate `no_persisted_three_original_day_directory` and `persisted_race_directories_unverified` results.
- A GitHub 403, unavailable branch, malformed response, inconsistent listing, oversized directory or unexpected member is **a failing audit**, never a source success. No collection is attempted and no archive bytes are rewritten.
- Added 10 synthetic regression tests to `tests/test_audit_t12_external_archive_presence.py`.
- Updated read-only PR audit workflow to generate `reports/official_three_archive_presence.json` beside the existing schedule-continuity report. This is metadata/negative evidence; neither report is an official raw-source witness.

[Exact-head GitHub Actions run #42477180382](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42477180382) succeeded, with **58/58 tests**: 12 schedule continuity + 20 source-pair/frozen + 16 three-original/frozen + 10 external archive presence. The workflow also performed the actual live GitHub readback with:

```json
{
  "day_jst": "20261108",
  "evidence_branch_commit_sha": "d0ed89f146dff117021c2bc042b20259d6715515",
  "existing_day_directories": ["20261103"],
  "day_directory_present": false,
  "race_directory_count": 0,
  "status": "no_persisted_three_original_day_directory",
  "full_t12_source_certified": false,
  "formal": false,
  "accuracy_scoring_allowed": false
}
```

## Root-cause handoff (not edits in this audit)

1. **Collector owner ①:** Establish why the every-five-minute intended official-pair collector had only one observed `event=schedule` run during the bounded Nov 8 watch; differentiate GitHub invocation scarcity from source HTTP status. Preserve official racelist/beforeinfo/odds three-original archives for current races in the dedicated durable evidence channel, as well as original Actions artifacts. Never reinterpret a green unrelated workflow as official three-source capture.
2. **Collector/model lineage owner ①:** Produce *new*, prospectively frozen forecast after latest verified source receipt and before official T−12, independently preserving actual input consumption and first GitHub remote acceptance. The existing 10:12 and 10:17 forecasts cannot be backfilled to claim the later 14:15 source receipts.
3. **Independent T−12 auditor:** Re-audit remote original bytes from an exact immutable Git commit, verify same-race exhibition 6/6, odds 120/120, source identity, official deadline and distinct first remote save; only then report formal eligibility if every prerequisite is independently proven. Until then **formal 0 and accuracy denominator undefined**.

Keep Draft #1694 manual-review only. **No main merge, no source collector, workflow cron, model, Render, UI, archived original, or historical forecast altered.**
