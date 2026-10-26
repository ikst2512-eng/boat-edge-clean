# Isolated paired model comparison (research only)

Run: `python research_comparison/paired_compare.py approved_pairs.json --baseline clean-national-beta0.4 --candidate old-v199-combined`

Input is a JSON array with one object per race:
```json
{
  "race_key": "20261028-12-1",
  "deadline": "2026-10-28T15:30:00+09:00",
  "input_sha256": "64-character verified digest",
  "result": "1-2-3",
  "research_outcome_access_approved": true,
  "outcome_independently_verified": true,
  "pre_registration": {
    "baseline_model_id": "clean-national-beta0.4",
    "candidate_model_id": "old-v199-combined",
    "baseline_model_sha": "40-character audited SHA",
    "candidate_model_sha": "40-character audited SHA",
    "registered_at": "2026-10-28T15:00:00+09:00",
    "receipt_verified_independently": true
  },
  "forecasts": {
    "clean-national-beta0.4": {
      "model_id": "clean-national-beta0.4",
      "model_sha": "audited model Git SHA",
      "input_sha256": "same digest",
      "first_git_commit": "audited initial addition SHA",
      "first_git_saved_at": "2026-10-28T15:10:00+09:00",
      "generated_at": "2026-10-28T15:09:00+09:00",
      "source_received_at": "2026-10-28T15:08:00+09:00",
      "independently_verified": true,
      "probabilities": {"1-2-3": 0.01}
    }
  }
}
```
The example probabilities are intentionally incomplete; **all exactly 120 strictly positive probabilities summing to 1** are required for both models. No historical outcomes may be used to reconstruct or backfill forecasts.

Independent preparation requirements:
1. Pre-register both exact model source SHAs and candidate selection before reviewing outcomes; record pre-specified evaluation interval and exclusions.
2. Verify first Git-addition SHA/timestamp against immutable original byte content, cutoff, source HTTP retrieval time and hash; the boolean flags in this input are declarations, **not** verification by this tool. Keep independent receipt audit externally.
3. A common `input_sha256` is mandatory, and all input features must have been available before the same cutoff. A feature not available to both models is not silently imputed. To compare richer old models fairly, run both from the same captured pre-cutoff source envelope; then lock both predictions before results.
4. Formal Fresh PRE_RESULT/result-unseen data are **out of scope** until separately authorized. Never read locked outcomes to populate this file.
5. This evaluator does not fetch inputs, predictions or outcomes, does not modify site files and cannot certify accuracy without audited records.
6. Each race is paired. Top1/3/5/10 deltas use paired bootstrap intervals and sign-flip randomization p-values. Log loss uses the realized exact trifecta's normalized probability. Top-1 ECE is descriptive and is unstable when the sample is small. Account for multiple tests and correlated races before any promotion.
7. Run `python -m unittest discover -s research_comparison -p 'test_*.py'`. Synthetic smoke tests do not establish accuracy.

**Known blockers (2026-10-27)**: the clean research snapshot currently persists top-10 tickets only, not the entire 120 distribution with independently verified first Git-addition and model SHA. Old V199 variants depend on a first-frozen V185 parent and source evidence; no eligible common prospective paired dataset is established. Hence current comparative hit rate, log loss and calibration are **not estimable**. Do not declare improvement or merge model weights.

Repository baseline SHA at preparation: `12db90df4fb82c364a70bfb63365ccccee1d7e0b`. Separate draft PRs #12, #14 and #15 own provenance/formal/source safety; do not overwrite them.

## Offline initial Git-addition audit

`python research_comparison/audit_first_git_add.py --repo ./independent-clone --commit <40hex> --path frozen/forecast.json --sha256 <64hex> --deadline 2026-10-28T13:00:00+09:00`

This read-only audit requires a single-parent commit that **adds** the named path, matches the exact stored bytes' SHA-256 and has a committer timestamp before the deadline. It rejects modifications masquerading as first additions. A trusted platform-side delivery timestamp, receipt/signature and source authenticity **must still be verified independently**, because a local Git committer timestamp can be backdated. It never automatically sets the evaluator's self-declared `independently_verified` field or unlocks outcomes.

## Integration warning

PR #16 independently implements a paired evaluation script. Its changed paths do not collide with this PR, but the algorithms overlap. Do not merge both as separate evaluation authorities; consolidate the evidence contract, tests and metrics after ownership review. The research evaluator here does not validate receipt status on its own. The initial prototype's test fixture SHA expressions were corrected to Python repetition syntax in commit 93b238c. GitHub Actions isolated research comparison checks passed at run #40375716887 for commit fa036741136cb91f6838732b3912fa631eabcc79. This is code-test evidence only, not a proof of prospective model performance.

## Explicit model-pair pre-registration gate

Each pair now requires a `pre_registration` object containing `baseline_model_id`, `candidate_model_id`, their exact `baseline_model_sha` and `candidate_model_sha` (40-character Git SHAs), `registered_at` as a timezone-aware ISO timestamp, and `receipt_verified_independently: true`. The timestamp must precede the deadline and both initial prediction freezes. A mere `candidate_pre_registered: true` Boolean no longer qualifies. An externally audited immutable receipt is still essential: the tool validates the claimed fields, but cannot establish their authenticity. Work from pre-registered cohorts rather than selecting good-performing candidates retrospectively. Do not use outcome data from locked Fresh records.

## Pre-result source chronology gate

Each model forecast must include `source_received_at` as a timezone-aware timestamp. The evaluator rejects absent receipts, sources received after forecast generation, and sources received at or after the official deadline. This checks timestamp consistency only; the source's actual arrival and authenticity must be verified against trusted external receipts. No historical reconstruction or locked Fresh result access is permitted.

## Exploratory sample gate

Fewer than 30 eligible paired races result in `INSUFFICIENT_EVIDENCE` even when descriptive metrics are output. This is an operational floor, **not** a power calculation or a proof that 30 races suffice. No sample count alone can authorize promotion without independently audited first-seen evidence, pre-registered cohort and source receipts, permitted outcomes and paired performance validation. Comparing a model against itself is rejected.

## Registration before prediction generation

The claimed model-pair preregistration must precede both forecasts' `generated_at` timestamps (not merely their first Git-saving times). This blocks registering a candidate after inspecting its prediction but before committing its file. The chronology remains self-reported until external first-seen receipts are audited.

## Canonical race identity

`race_key` must use `YYYYMMDD-VV-R` (eight-digit date, two-digit official venue code, race number 1–12). This is a format-only guard; official race existence and venue mapping require independent verification. Duplicate canonical keys are excluded.

The offline race-key gate also rejects impossible calendar dates, venue codes outside 01–24, race numbers outside 1–12, and dates inconsistent with the cutoff after converting it to JST. It **does not** verify that the event was actually held or that the cutoff is the official published deadline; those require independent official race-source evidence.

## Ambiguous duplicate race handling

All occurrences of a duplicated `race_key` are excluded, even if one appears otherwise valid. This avoids row-order-dependent selection of outcomes or forecasts. Diagnose and resolve upstream duplicates using independently authenticated original records; never select the outcome that favors one candidate.

## Exclusion audit trail

The output includes `excluded_details`, containing a race key and exclusion reason per rejected row, without copying result tickets, feature payloads or probability distributions. Duplicate race occurrences are all excluded. Treat this as diagnostic metadata, not independent proof of outcome access or prospectivity.

For excluded records, `race_key` is included in the audit trail only when it matches the canonical key syntax. Free-form or malformed identifiers are replaced with `null` so that injected result text or private feature data is not echoed by diagnostics.

## Snapshot completeness preflight

Use `python research_comparison/snapshot_preflight.py research_snapshots/<race_code>.json` to diagnose existing saved research files without reading outcomes. Current `research_model.py` and `collect_research_daily.py` save Top10 only, even though the model calculates 120 outcomes in memory. The preflight intentionally never returns `ready: true`: even a complete 120-way map still needs separately authenticated original bytes, source receipts, model registration and cutoff evidence. Never synthesize the missing 110 probabilities from after-the-fact data.

## Isolated prospective 120-way capture (new research samples only)

`research_comparison/prospective_120_capture.py` can freeze the current clean exploratory model's entire probability map into a **new**, independently named JSON snapshot. It accepts the six source rates, their claimed receipt time, cutoff, composite source digest and an externally verified exact model SHA; it checks the current system clock and creates the output exclusively (`xb` + fsync). Do not run this against old finished races, do not overwrite existing Top10 files, and do not copy records into production. The file's local creation time is **not** trusted external first-seen proof, and the command checks the supplied CSV bytes and their model-input race/rates, but does not independently verify Git model provenance or authentic external source receipt. Before using it for scoring, independently attest the original source receipt and byte provenance, model source and independent receipt, pre-register both models, retain 120-way snapshots for **both** models and confirm identical inputs. The stored 120-way research sample is not Formal Fresh and is not validated.

Prospective capture also rejects non-calendar race dates, venue codes outside 01–24 and race numbers outside 1–12 before creating output. These local checks do not verify the actual event or official cutoff; externally sourced receipts remain mandatory.

### Original-byte SHA256 gate

The prospective capture CLI now requires `--title-csv` and `--cards-csv` in addition to `--input-sha256`. Python callers provide `title_bytes` and `cards_bytes`. Matching PR #23, it hashes the raw title and race_cards CSVs separately, then computes SHA256 of the ASCII `title_sha256:cards_sha256` string. The order is significant; a mismatch rejects capture. The record stores both source digests and `input_hash_scope=source_csv_byte_hashes_ordered_title_cards`. This establishes byte-to-declared-hash consistency locally only; it does **not** establish that the file was independently received before cutoff, authentic or generated from the same source used by the model. Keep the independently time-stamped original and verify its provenance separately.

### CSV values bound to forecast

The independent 120-way capture now reads the unique matching `レースコード` row in both supplied original CSVs. It requires all six `艇1..6_全国勝率` values to exactly match supplied rates and the claimed `cutoff_jst` to equal `電話投票締切予定` minus 12 minutes. This rejects valid digests paired with unrelated model features or an arbitrary cutoff. Raw files and receipt times still require independent provenance review; local consistency is not official authenticity.

## Offline research snapshot bridge

Run `python research_comparison/snapshot_bridge.py path/to/frozen-120.json` to produce a comparison-shaped **unverified draft**. The adapter verifies the ordered PR #23 CSV digest chain, all 120 ticket keys and agreement of stored Top10 with probabilities. It reports `ready_for_scoring: false` and lists independent audit blockers. It never invents first Git commit/time, verified receipts, model pre-registration, official results or deadlines, and does not touch production, locked Fresh data or results. Passing a draft directly to `paired_compare.py` must exclude the race until independent provenance has been established and reviewed.

## PR #16 integration boundary

PR #16 already implements a separate prospective paired capture for the exploratory baseline and scenario candidate. Do not silently replace its paired freeze or treat its model blob ID as an independently attested commit SHA. PR #17's `snapshot_bridge.py` is a format/provenance preflight for its own full-120 snapshot: it now enforces finite positive normalized probabilities. Neither pipeline can declare a validated race pair until both immutable forecasts, shared original-source digest, model identities, independently authenticated pre-deadline receipts, registered cohort and permitted official result have been audited. Merge neither research draft as a production model promotion.

The snapshot bridge rejects invalid calendar/venue/race identity and inconsistent self-declared chronology (`source_received_at` after `generated_at`, generation at or after safety cutoff, or mismatched JST race date). This is only a local consistency check, **not** an authenticated first-seen timestamp. The paired evaluator still requires independently verified formal cutoff and permitted result.

## PR #16 pair-file diagnostic

Use `python research_comparison/pr16_pair_preflight.py research_prospective_pairs/<race_code>.json` to check structural completeness of PR #16's baseline/candidate distributions and claimed freeze chronology. It does not query results, edit forecasts, perform score calculations, or certify server receipt evidence. `ready_for_scoring` always remains false, even for structurally valid pairs, until authenticated receipt, preregistration, original source and outcome audit are performed outside this tool. PR #16's `research_remote_pair_evidence.py` can check a GitHub Actions push-run timestamp and exact pair bytes, but this alone does not independently verify the source data or the two model implementations.

PR #16 pair preflight additionally diagnoses malformed race identities, missing source snapshot SHA256, missing baseline/candidate IDs, and malformed candidate model Git blob identifiers. These syntactic checks do not prove that the candidate blob corresponds to source code or that remote pair publication occurred before cutoff.

To bind a PR #16 pair to its original source snapshot, run `python research_comparison/pr16_pair_preflight.py research_prospective_pairs/<race_code>.json --source-snapshot research_snapshots/<race_code>.json`. The tool recomputes the PR #16 canonical JSON SHA256 (`ensure_ascii=False`, sorted keys and compact separators) and checks the original race identity. Omission of `--source-snapshot` leaves this original-byte verification **unperformed**; no authenticated external receipt is inferred.

The PR #16 pair preflight now reports `source_snapshot_digest_verified_locally` and adds an explicit `source snapshot original bytes not supplied` reason when `--source-snapshot` is omitted. A true local flag is **not** independent receipt verification; `ready_for_scoring` remains false until external audits are complete.

Original snapshot audit now requires the source JSON envelope to be `status: research` and `validated: false`, even when its canonical JSON SHA256 matches the pair's declared digest. Non-research records and invalid pair envelopes are never reported as valid local evidence or complete distributions.

The optional PR #16 source snapshot check also requires its declared generation timestamp, cutoff, and original Top10 predictions to match the paired baseline's Top10 rank. A SHA-consistent but mismatched snapshot is not marked locally verified. This remains a consistency check rather than proof of actual GitHub publication time.
