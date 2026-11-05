# Legacy BOAT EDGE preservation decision matrix — 2026-11-04 JST

Scope: read-only retirement handoff for [#708](https://github.com/ikst2512-eng/boat-edge-clean/issues/708) and [#329](https://github.com/ikst2512-eng/boat-edge-clean/issues/329). No forecast import, no producer/CI/UI changes, no job disablement, no deletion. This is a **gate register**, not an assertion that migration or an independent backup has occurred.

## Source pointers and immutable inspection baseline

- Legacy `ikst2512-eng/boat-edge`, inspected main commit `5e0341f0a0299428d460c72049d18b2e5857f608` (2026-11-03 UTC).
- CLEAN `ikst2512-eng/boat-edge-clean`, inspected main commit `d88fa2e659240ae97f1771cfd1174a058c1d5b14` (2026-11-03 UTC).
- Pre-existing measured gap: [legacy-evidence-gap-20261029.md](legacy-evidence-gap-20261029.md). File counts there are **as-of 2026-10-29**, not current counts. Path mismatch is not content mismatch.
- Prior verified result-only archive: workflow `40936953310`, 412 matched result blobs restored SHA256 at the time; artifact `12924304439` has an expiry and is **not** independent long-term retention.
- Cross-model run `41556670332` on CLEAN SHA `eff4975851744a9851ce82383c79662b76496747`: 1046 race-ID overlaps, 108 actual Top10 comparisons, 938 without comparable dual prediction originals, 108 legacy workflow YAML according to run report. Existing artifact `13194783484` (`cross-model-audit-evidence`), expires `2026-12-03T01:06:26Z`, GitHub-reported ZIP digest `sha256:0823d71201fc51ddb9d08021a557f469bd4acbb2980205a0e916c1159aad7831`. **Artifact existence/digest is not a claim that this pass independently downloaded and restored its bytes.**
- Historical six-racer / confirmed-result / 120-odds Render tests in #708 are isolated samples and do not constitute continuous, predeadline CLEAN autonomy.

## Preservation matrix

| Legacy source / component | Essential proof to preserve | Cross-system identity check | Status / disposition |
| --- | --- | --- | --- |
| `data/site_prediction_snapshots/` | Original ticket ordering, model identifier, race key, generation and deadline metadata, exact bytes | First-add Git commit/time + source blob SHA + SHA256 + CLEAN model identity kept separate | **KEEP — independence/restore unproved** |
| `data/site_prediction_audit/` | Original freeze eligibility, receipt/order checks, attestations, first Git write | Connect each audit to a specific prediction and immutable Git object | **KEEP — provenance pending** |
| `data/site_prediction_history/` | Earlier/revised versions and first-observed history | Check full chronological commit chain; do not infer first-save from JSON timestamp | **KEEP — provenance pending** |
| `data/site_odds/` | 120-way predeadline odds, acquisition timestamp, official source, race key | Link to prediction input at the exact applicable time; verify 120 unique combos | **KEEP — source matching pending** |
| `data/raw/` | Specific pre-result card/exhibition/ST/scratches/raw source bytes used by a forecast | Trace from frozen forecast to input files and source-receipt times | **KEEP — select by dependency, not full-directory copy** |
| `data/site_results/` | Confirmed finish, payout, official source and original revisions | Match race key, finish and 3T payout; preserve mismatches separately | **KEEP — 412 restored result examples do not prove comprehensive parity** |
| `data/site_autopilot/` | Formal Fresh cohort, freeze/score provenance, immutable pre-/post-result boundary | Require formal eligibility and first-save proof; no research-to-formal upgrade | **KEEP — formal necessity/restore pending** |
| V13 classifier code/tests | Versioned reproducibility of legacy classification | Pin code/test blob SHA and relevant historical artifact to result | **KEEP — reference only; do not import into CLEAN runtime by default** |
| Legacy Actions and Pages | Active trigger/writer/consumer links, URLs, recovery paths | Per-workflow evidence: schedule/manual/workflow_run/push, contents permission, last real run, same-path writes, replacement, rollback | **REVIEW_REQUIRED — no stop** |

## Direct workflow read inspection

| File | Observed trigger / permission | Risk if disabled |
| --- | --- | --- |
| `.github/workflows/auto-update.yml` | `*/5 * * * *`, V71 `workflow_run`, `contents:write` | PRE_RESULT collection and Git evidence may stop |
| `.github/workflows/site-odds.yml` | 12 wakes/hour, `contents:write`, 120-way official odds validation | Immutable input odds supply may stop |
| `.github/workflows/V235.yml` | `workflow_run` of source producers + schedule, `contents:write` | prospective first-freeze evidence may stop |
| `.github/workflows/BOAT_EDGE_V229_ATOMIC_FREEZE_AUDIT.yml` | independent source-triggered and scheduled freeze, `contents:write` | strict first-save attestation may stop |
| `.github/workflows/pages-controlled-publish.yml` | controlled Pages publish, requires Pages `build_type=workflow`; schedule + `workflow_run` | old public URL may lose its publisher |
| `.github/workflows/boat-edge-v350-actions-evidence.yml` | manual/read-only evidence exporter, `actions:read`, `contents:read` | Actions execution evidence/diagnostics may be lost |

These are **static config observations**, not proof of a specific latest successful run or a complete 108-workflow dependency graph. No other workflow is classified safe-to-delete here.

## Required per-race proof ledger (before any retirement)

For every legacy-exclusive forecast, preserve a machine-readable, non-public or archival **index** with:

`race_key, original_repo, original_path, original_blob_sha, original_sha256, first_add_commit_sha, first_add_commit_time_utc, source_capture_time_jst, forecast_generated_time_jst, deadline_jst, model_id, picks_top10, odds_source_path, odds_blob_sha, odds_sha256, raw_input_paths_and_shas, confirmed_result_path_sha, payout_evidence_sha, formal_eligibility_status, backup_store_id, restored_sha256, restore_verified_at`.

- Hash **original bytes**, and make a restored copy in independently retained storage (not a 30/90-day Actions artifact); **read back** and compare hashes.
- Never invent unknown evidence fields: use `null` and mark `BLOCKED`. Existing legacy source JSON timestamps are not equivalent to first Git add.
- Keep research and formal Fresh distinct. Results/odds after cutoff cannot retroactively certify a predeadline original.
- No secrets or tokens in logs, commits, issues, or public manifests. Avoid bulk-mirroring potentially sensitive raw payload into CLEAN's public repo.

## Release gates, owner boundaries and rollback

1. **Backup gate** — per-race original/first-add/source/odds/result/provenance index, independent durable copy, SHA256 read-back and sampled full reconstruction. Owner: legacy migration. **Open**.
2. **Dependency gate** — every workflow's last actual runs, call graph, writes, Pages source, secrets references (names only), and external consumers; distinguish active from merely present. Owner: legacy migration. **Open**.
3. **Replacement gate** — CLEAN main SHA equals deployed Render/Pages version; selected race live predeadline six-racer/exhibition/120-odds and confirmed-result proof over consecutive autonomous scheduled windows. Owner: UI/Render and precision teams; this team consumes evidence only. **Open**.
4. **Reversible retirement gate** — only after 1–3: individual old writers/publisher with explicit rollback SHA, restore procedure, user-facing old-URL migration notice, monitoring and contingency. **Not authorized**.
5. **Final archival/deletion gate** — long-lived independent restore + external link impact validated, separate approval; archival precedes any deletion. **Not authorized**.

**Decision: `DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED`.** This document adds no active workflow, modifies no model/result/odds originals, and authorizes no shutdown.
