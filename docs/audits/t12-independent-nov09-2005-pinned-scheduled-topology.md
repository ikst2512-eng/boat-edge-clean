# 2026-11-09 20:05 JST — PINNED main source-collection topology: missing automatic racelist link

**Independent, audit-only PR #1694.** This is a narrowly scoped actual GitHub-code audit, not a production code change, not a GitHub scheduler root-cause claim, and not a formal forecast certification. **Formal T−12 verified forecasts = 0; formal accuracy denominator undefined.**

## New material finding: why adding scheduled activations is not sufficient

At immutable main SHA `4bd080ad77778053575cf497c8a6b85b959ce173` the audit fetched five original source files from the real GitHub repository contents API, independently recomputed and matched the **Git blob SHA1** for each source (no local/generated surrogate treated as evidence), parsed three top-level workflow trigger declarations, and checked the actual Python direct source-import dependencies.

| Audited source path | Observed effective configuration |
|---|---|
| `.github/workflows/research-live-preview-evidence.yml` | Has UTC `*/5 0-12 * * *` schedule and invokes `python -m scripts.capture_joint_preview_batch` once. |
| `scripts/capture_joint_preview_batch.py` | Directly imports and calls official `capture_official_beforeinfo_json` and `capture_official_odds_receipt`. **It does not import or invoke official racelist capture**. The existing 11/9 actual artifact proves valid two-source pairs sometimes succeed, but no third source was present in that pair ZIP. |
| `.github/workflows/official-three-original-t12-observation.yml` | Has `workflow_dispatch` and `pull_request`, **no schedule**; the `observe` job is explicitly guarded by `github.event_name == 'workflow_dispatch'`. Its old Nov 3 scheduled observation was retired to avoid reusing stale race IDs. |
| `scripts/observe_three_official_t12_originals.py` | The separate working research code does have three direct official capture dependencies: beforeinfo, racelist, odds, but is only wired to the manual observation workflow above in this bounded topology. |
| `.github/workflows/official-racelist-live-dispatch.yml` | Has `workflow_dispatch` and a path-scoped `push` for changes to that workflow file. **No `schedule`**. This is *not* dispatch-only (a workflow-file push can invoke it), but it is not an ongoing scheduled racelist collector. |

**Definitive bounded conclusion:** the currently inspected and actually observed `research-live-preview-evidence.yml` scheduled pair-capture execution does **not directly** acquire the third official racelist source. The two selected manual research workflows do not provide a scheduled third-source chain. Accordingly, merely repairing the sparse schedule activations of the **existing two-original capture** does not establish a same-run, same-race official *three-original* source chain, let alone a post-source prediction.

**Scope limits, deliberate:** This is static verification of **five named GitHub files at one pinned main commit** and the direct collector imports. It is **not an exhaustive analysis of all repository workflows**, not evidence that no third original exists anywhere else, not proof that a particular cron slot was skipped, and not proof of any real HTTP fetch by itself.

## Actual independent replay and run metadata still constrain any positive claim

The exact-head audit CI also successfully re-ran:
- 11/03 pinned official *three-original filenames* for 桐生12R: valid racelist 6 identities and 120 odds, **missing 6/6 exhibition time, tilt, ST and course**. Not ready.
- 11/09 schedule-run `42567310743`: complete official two-original six-boat exhibition/120 odds pairs for **宮島10R and びわこ10R**, source-archive GitHub timestamp **14:27 JST** before cutoffs, but no official racelist raw original in the pair archive. The four pinned CLEAN/V2 forecasts were generated hours **before** source receipts. Not certifiable.
- Same-race proof chain: **zero qualified three-original T−12 source races**, zero verified post-official-source frozen forecasts and zero formal certification.

At **20:05 JST**, live current-day GitHub API reported **one** observed source-pair `event=schedule` run creation versus **134 elapsed nominal five-minute time slots** since 09:00 JST (observed-to-nominal count ratio **0.75%**). This is a **creation-count gap**, *not* proof that 133 specific cron slots were dropped or 133 HTTP requests failed. The dedicated `research-t12-external-evidence` branch stayed at immutable SHA `d0ed89f146dff117021c2bc042b20259d6715515`, with no November 9 durable three-original race directory in that branch; other temporary artifacts are not excluded by this branch-only inventory.

## Implementation

- `scripts/audit_t12_scheduled_source_topology.py` performs **authenticated pinned GitHub readback** with file identity, size, base64 and raw Git blob SHA1 verification, parses selected actual GitHub workflow event blocks, and reads actual Python AST direct imports; emits machine-readable `reports/official_t12_scheduled_source_topology.json`. It always reports `formal=false`, `accuracy_scoring_allowed=false` and `formal_accuracy_denominator=null`. It fails closed if any selected workflow or import graph changes; owner-side future fixes should trigger **re-audit**, not silently carry old conclusions forward.
- `tests/test_audit_t12_scheduled_source_topology.py`: **16 regression tests** including changed cron, new scheduled triad, missing manual dispatch guard, false scheduled racelist claim, missing Git original blob, invalid repo/ref, and scope overclaim guards.
- `.github/workflows/audit-official-pair-schedule-continuity.yml`: new read-only pinned source step and separate report artifact.

[Exact code-head CI #42606135227](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42606135227) at `820a510c0185eafe43c81bb2b58a9fbe5edced7c`: **SUCCESS 196/196 audit unit tests** (previous 180 + 16); the **actual remote pinned Git five-source inspection succeeded**, and all original archived source/forecast replays continued to succeed. Source topology report sets `scheduled_official_pair_directly_captures_racelist=false`, `dedicated_triple_observation_has_schedule=false`, `racelist_only_workflow_has_schedule=false`, `other_repository_workflows_exhaustively_audited=false`, `formal=false`. A distinct CLEAN prospective independent accuracy-check workflow has continued historical first-add rejects; **do not conflate passing source audit with all CI green or a proven accuracy lift**.

## Immediate implementation handoff to source collection owner ①

1. **Restore actual reliable recurring source capture**, using the previously measured sparse runs across multiple scheduled workflows as investigation evidence, not as a presupposed GitHub platform failure.
2. **Connect the official racelist original into a genuinely prospective, same-race source workflow or independently correlated capture path.** The acquisition must prove exact six racer registration identities, preserve immutable original racelist HTML/URL/hash+timestamps and link that to the same race's exhibition-ready six-row official beforeinfo and 120 unique odds original with actual T−12 cutoffs. Avoid using a retired static 2026-11-03 race-code matrix.
3. **Model/forecast owner:** generate a new immutable official-source forecast *after* all three original receipts but *before* official T−12; independently replay that those raw originals influenced the model. Record first **forecast GitHub remote acceptance**, independently from local author/committer timestamps and independently of the source ZIP server `updated_at`; verify final declared entries.
4. Keep pre-existing CLEAN/V2 public-CSV early predictions unchanged; never backfill or automatically promote the November 3/9 examples to official accuracy statistics.

**No main merge, no production collector/model/Render/UI modifications, no automatic approval. Draft PR #1694 remains pending independent review.**
