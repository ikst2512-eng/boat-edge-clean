# 2026-11-09 20:15 JST — all 149 pinned-main GitHub Actions workflows independently scanned

**Read-only, nonformal, Draft PR #1694.** No main merge/changes, production collection, GitHub Actions source workflow, Render, model, UI, historical forecast or source bytes modified. Formal T−12 certification **0**; formal accuracy denominator undefined.

## Scope and result: real immutable Git tree, not an assumed list of five files

One *additional, isolated read-only checkout* of immutable main commit `4bd080ad77778053575cf497c8a6b85b959ce173` was used. `scripts/audit_t12_full_workflow_inventory.py` first requires the local Git checkout HEAD to be **exactly** the pinned main commit, then recursively enumerates all tracked `.github/workflows/*.yml` or `.yaml` files using `git ls-tree`. It reads every original blob with `git cat-file blob`, independently checks its Git blob SHA1 against the pinned tree, parses top-level GitHub Actions `on:` declarations, and identifies literal direct references to official 3-original / racelist capture code in scheduled-workflow source text. The full per-file path, content SHA1, declared events and matching lines are persisted in the separate report.

[Actual exact-code-head audit CI #42607489094](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42607489094), code commit `8f84980e180b933eafe69bd5b7f5f0c8fc918945`, **SUCCESS**:

| Measure | Actual result |
|---|---:|
| Tracked workflow YAML files at pinned main | **149** |
| Workflow files with classifiable top-level trigger events | **149/149** |
| Declared `schedule` workflows | **51** |
| Scheduled workflow YAMLs containing explicit direct `observe_three_official_t12_originals` / `capture_official_racelist_receipt` invocation text | **0** |
| Git blob SHA1s checked against immutable main tree | **149/149** |
| Independent audit-only unit tests | **210/210 passing** |
| Qualified same-race original source triads from previously reaudited 3-race cohort | **0** |
| Newly formally certified T−12 forecasts | **0** |

The CI artifact `reports/official_t12_all_main_workflow_inventory.json` includes all 149 path+SHA+event rows and all 51 scheduled workflow paths. The workflow trigger parser marked **0 unclassified** event declarations, so no workflow was silently excluded from the scheduled count. The other original source/forecast replay reports still passed in the same CI.

### Critical bounded interpretation: DIRECT references only

A zero direct-reference count **does not prove zero transitive or indirect official racelist captures**. A scheduled workflow may execute a local shell/Python script or a reusable/external action that itself calls the official racelist code without the filename appearing in the workflow YAML. This audit does **not** execute or resolve those call graphs, HTTP endpoints, GitHub reusable workflows, script imports, nor assert whether any scheduled events actually ran. It is also an immutable historical snapshot at a specific main commit, not proof of later main revisions.

The previous stricter [five-file pinned topology audit](https://github.com/ikst2512-eng/boat-edge-clean/blob/audit/t12-nov06-day-isolation-20261106/docs/audits/t12-independent-nov09-2005-pinned-scheduled-topology.md) *did* inspect the direct imports of the **observed** source-pair collector: `.github/workflows/research-live-preview-evidence.yml` invokes `scripts.capture_joint_preview_batch`, and that Python script imports official beforeinfo and odds capture but **not** official racelist capture. The separate three-original research workflow has `workflow_dispatch` only for its observation job; dedicated racelist workflow has manual/path-scoped push, not a recurring schedule.

Other schedules such as `late-preview-capture.yml`, `entry-course-t12-baseline.yml` and `clean-prospective.yml` exist and were included among the 149. Some may indirectly collect race information; their transitive code dependencies have **not** been fully proven incapable of satisfying an official three-original chain. Do not interpret this scan as a comprehensive negative audit of all code.

## Same 2026-11-09 time-bound source gate

At source CI ~20:15 JST, the official two-original collector `.github/workflows/research-live-preview-evidence.yml` had **one** observed `event=schedule` run creation out of **136 nominal five-minute slots elapsed** (ratio **0.74%**), and the separate permanent `research-t12-external-evidence` branch at pinned SHA `d0ed89f146dff117021c2bc042b20259d6715515` still contained **no Nov 9 original-triad race directory**. The gap is a **count difference**, not 135 proved HTTP failures or individually proved skipped cron events. Root cause of low schedule creation counts remains unverified.

Prior real original replay continues to show:
- Nov3 桐生12R: actual three original filenames, but **exhibition times/tilt/start display incomplete**.
- Nov9 宮島10R and びわこ10R: **two complete official beforeinfo/exhibition+odds pairs**, and authenticated GitHub original-source artifact server timestamps before official T−12, but no third same-race racelist original in the pair archive, and all four immutable CLEAN/V2 forecasts predate the official original receipts.
- **No fully qualified same-race three-original source set; no source-following new frozen forecast; no independent first forecast Git remote acceptance; no formal accuracy denominator**.

## New audit-only implementation and validation

- `scripts/audit_t12_full_workflow_inventory.py` — bounded static original-Git-source inspection, explicit unknown-classification and indirect-acquisition limitations, exact pinned SHA and 149-file count fail-closed.
- `tests/test_audit_t12_full_workflow_inventory.py` — **14 cases** including duplicate/missing `on` declarations, unknown YAML forms, inline schedules, forged source paths, missing checkout or wrong Git ref, Git blob SHA and zero formal-certification safeguards.
- `.github/workflows/audit-official-pair-schedule-continuity.yml` — separate GitHub checkout `persist-credentials:false` of exact historical main SHA, read-only full scan and separate immutable-source audit artifact upload. No editing of existing source collection workflow.

The distinct `CLEAN prospective independent accuracy checks` remains blocked by earlier first-add/remote-acceptance evidence; **210/210 success is the independent source-audit test count, not a claim that every CI has passed or forecast accuracy improved.**

## Owner① immediate next action

1. Review the **51 scheduled workflow direct commands and transitive import chains**, beginning with the observed source-pair collector, any scheduled `late-preview` and `entry-course` collectors and forecast scripts; distinguish direct official racelist source receipts from derived CSV racecard entries.
2. Correct genuine recurring activation reliability *and separately* incorporate an immutable official racelist original into a prospective **same-race** six-boat exhibition-ready beforeinfo and 120-way odds pipeline; each source hash, official URL, original-byte replay and receipt time must be independent and before the real T−12.
3. Create a genuinely new model prediction **after** the last of those three source receipts but **before** T−12 and prove model raw-source consumption, initial forecast GitHub remote acceptance and final entry. Never retrospectively convert old CSV CLEAN/V2 predictions into official evidence.
4. Leave this audit-only PR Draft and unmerged. Source collection changes and production rollout belong exclusively to owner①'s scoped PR, not this audit.

**No main automatic merge, no production change, no formal scoring authorization.**
