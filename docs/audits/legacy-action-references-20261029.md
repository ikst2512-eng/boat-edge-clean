# Legacy GitHub Actions audit — verified run 40752272665

Source: https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/40752272665
PR: https://github.com/ikst2512-eng/boat-edge-clean/pull/199
Artifact: `legacy-action-references`, ID `12843463776`, SHA256 `c3219c2b33fa8522e1ad51cdb5bb54f7fa2d76e37d58c58b4bacd387587c0b2e`.
Legacy tree SHA: `8ab7a7ae6c466059f98a1cdcca0195ffe7b1e6b8`.

## Confirmed counts
- Workflow YAMLs read: **105**
- With textual inbound references from another workflow: **15**
- Without detected textual inbound references: **90** (NOT deletion-safe)
- With `workflow_dispatch:` literal: **88**
- With `schedule:` literal: **37**
- With `workflow_run:` literal: **10**
- Authorized deletions: **0**
- Audit workflow: **success**; unit test and artifact upload both passed.

## Referenced workflows to preserve pending deeper audit
```text
.github/workflows/BOAT_EDGE_DEADLINE_EVIDENCE_V9.yml
.github/workflows/BOAT_EDGE_V216_SOURCE_DIAGNOSTIC.yml
.github/workflows/BOAT_EDGE_V228_SITE_AI_AUTOPILOT.yml
.github/workflows/BOAT_EDGE_V229_ATOMIC_FREEZE_AUDIT.yml
.github/workflows/BOAT_EDGE_V230_FAST_OFFICIAL_PREDEADLINE.yml
.github/workflows/V234.yml
.github/workflows/V235.yml
.github/workflows/auto-update.yml
.github/workflows/site-odds.yml
.github/workflows/site-results.yml
.github/workflows/v236.yml
.github/workflows/v237.yml
.github/workflows/v238.yml
.github/workflows/v240-autodev.yml
.github/workflows/v241.yml
```

## Necessary checks before any deletion
1. Pin legacy repository to an immutable commit/tree and preserve input/output, workflow YAML and source checksums.
2. Check direct `workflow_call` and `uses:`, API dispatches, reusable actions, externally triggered jobs, and indirect file/data dependencies; current detection is substring-only.
3. Check operational triggers and historical executions, including schedules, dispatches, `workflow_run`, and any external actors. A zero inbound-match is not evidence of inactivity.
4. Validate equivalent functionality in CLEAN, including dataset parity and production evidence.
5. Require explicit per-workflow approval with regression results, rollback plan, and confirmation that official Fresh evidence stays immutable.
6. Do not delete in legacy repo based only on this report.

This document reports observed run data; it is not an authorization to delete workflows.
