# 2026-11-09 — 51 scheduled workflow transitive route review (independent, read-only)

Status: Draft PR #1694 only; **not** T-12 certification. No main merge, source collector, cron, model, UI or Render modification.

## Verified exact-head CI and immutable scope

- [Read-only CI #42609744880](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42609744880): SUCCESS at audit head a560283445e7a3f6345064a0271baf8aab15f3da.
- Source tree pinned to immutable main SHA 4bd080ad77778053575cf497c8a6b85b959ce173.
- 149 workflow YAMLs scanned; 51 declare schedule; static script-import/command reachability finds 1 scheduled workflow with a potential official racecard AUDIT reference; 50 scheduled workflows have some unknown/out-of-scope element (including ordinary external Actions). These 50 are NOT 50 proven capture routes or failures.
- New standalone transitive scanner and 13 independent regression tests passed. The full 51-row JSON is archived in artifact official-pair-schedule-audit-42609744880, artifact ID 13670011394, output file reports/official_t12_51_scheduled_transitive_static.json.
- Each pinned local Git blob traversed is checked against its Git tree SHA1. Auditor performed no live boatrace HTTP fetch or collection.
- Source-only graph is not execution evidence, and its absence of an additional candidate is not negative certification.

## One observed candidate path: archived source auditor, not live collector

The pinned tree contains this import chain:

    .github/workflows/official-three-original-t12-reinspect.yml
      -> scripts/reaudit_scheduled_three_t12.py
      -> scripts/audit_three_official_t12_originals.py
      -> scripts/audit_official_racelist_receipt.py

The workflow has a date-limited one-day schedule for November 3, 2026 (25 7 3 11 *) and the job exits on scheduled events on any other UTC day. Its script downloads historic GitHub Actions archives and re-audits their saved source files. The last module reads local racelist.html/manifest.json/beforeinfo.json and compares the saved manifest's original official racelist URL against an expected URL. This is an archived-data identity check, not a fresh boatrace.jp request. No call to live capture_official_racelist_receipt or observe_three_official_t12_originals was established in this chain. Static import reachability does not prove the code branch actually ran.

## Other verified original producer gaps

- Scheduled research-live-preview-evidence.yml invokes scripts.capture_joint_preview_batch; its module imports official beforeinfo and official odds capture but no official racelist capture. The pair cannot be promoted to a three-original source chain.
- Scheduled late-preview-capture.yml calls the legacy CSV/evidence row collector. Its official beforeinfo HTML diagnostic probe is manually gated, not the recurring path.
- Scheduled entry-course-t12-baseline.yml freezes research forecast seeds, not original official racecard+beforeinfo+odds receipts.
- Scheduled clean-prospective.yml collects supported existing upstream candidate inputs and prospective forecasts; those are not automatically verified same-race official three-original evidence or independently accepted remote Git first-add.
- The full earlier direct reference check remains 0 matches in the 51 scheduled YAML sources. Direct zero is not transitive zero.

## Explicit uncertainty and collection owner ① action items

1. **Finish runtime-path classification:** inspect flagged external/local Actions, shell expansion, subprocess/importlib, dynamic dispatch, reusable workflow internals and scheduled branch guards. Separate routine checkout/setup actions from application-specific unknowns. Record an exact reproducible source and observed run/path for any real official racelist HTTP acquisition. The historical reinspection candidate above is not a new producer.
2. **New real same-race triad:** in owner ①'s separately approved scoped collection PR, acquire and durably archive official racecard HTML, official beforeinfo JSON and all 120 unique official trifecta odds combinations for the identical race code. Preserve original bytes, canonical source URLs, SHA256, source receipt times and server archive proof. Verify six registration IDs, six exhibition times/ST/tilt, exhibition/course mapping and authoritative cutoff before real T-12. Missing data must fail closed.
3. **Source-following new forecast:** only after the three matching originals and before the real T-12, create a genuinely new prediction with verifiable raw-source consumption and immutable input hashes. Independently prove FIRST successful remote Git receipt and immutable prediction path before cutoff, followed by separate final-entry confirmation. Never retroactively convert historic CLEAN/V2 records into official evidence or join sources from different race days.
4. **Reliability separately:** audit scheduled run creation versus intended slots and distinguish scheduling, HTTP attempts, successful complete originals, artifact publication and remote prediction acceptance. Do not turn nominal missed slots into fabricated HTTP failures.

**Formal qualified same-race triads newly proven by this audit: 0. Formally certified forecasts: 0. Formal accuracy denominator: undefined.** No accuracy improvement is claimed. Preserve #1694 as Draft and unmerged; no automatic main merge, production source changes or paid recurring jobs.

## Reproduction

Run from the PR checkout with a second separately pinned read-only Git checkout at the main SHA above:

    python -m unittest discover -s tests -p test_audit_t12_scheduled_transitive_routes.py -v
    python -m scripts.audit_t12_scheduled_transitive_routes --pinned-checkout pinned-workflow-main --output reports/official_t12_51_scheduled_transitive_static.json

Wrong pinned HEAD or the expected 149/51 workflow counts fail closed. Scanner output always retains no_indirect_capture_proven=false, official_http_capture_proven=false, formal=false, new_formal_certifications=0, formal_accuracy_denominator=null.
