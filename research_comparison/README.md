# Isolated paired model comparison (research only)

Run: `python research_comparison/paired_compare.py approved_pairs.json --baseline clean-national-beta0.4 --candidate old-v199-combined`

Input is a JSON array with one object per race:
```json
{
  "race_key": "YYYYMMDD-venue-race",
  "deadline": "2026-10-28T15:30:00+09:00",
  "input_sha256": "64-character verified digest",
  "result": "1-2-3",
  "research_outcome_access_approved": true,
  "outcome_independently_verified": true,
  "candidate_pre_registered": true,
  "forecasts": {
    "clean-national-beta0.4": {
      "model_id": "clean-national-beta0.4",
      "model_sha": "audited model Git SHA",
      "input_sha256": "same digest",
      "first_git_commit": "audited initial addition SHA",
      "first_git_saved_at": "2026-10-28T15:10:00+09:00",
      "generated_at": "2026-10-28T15:09:00+09:00",
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

PR #16 independently implements a paired evaluation script. Its changed paths do not collide with this PR, but the algorithms overlap. Do not merge both as separate evaluation authorities; consolidate the evidence contract, tests and metrics after ownership review. The research evaluator here does not validate receipt status on its own. The initial prototype's test fixture SHA expressions were corrected to Python repetition syntax in commit 93b238c. No completed GitHub Actions test run has yet been demonstrated.

## Explicit model-pair pre-registration gate

Each pair now requires a `pre_registration` object containing `baseline_model_id`, `candidate_model_id`, their exact `baseline_model_sha` and `candidate_model_sha` (40-character Git SHAs), `registered_at` as a timezone-aware ISO timestamp, and `receipt_verified_independently: true`. The timestamp must precede the deadline and both initial prediction freezes. A mere `candidate_pre_registered: true` Boolean no longer qualifies. An externally audited immutable receipt is still essential: the tool validates the claimed fields, but cannot establish their authenticity. Work from pre-registered cohorts rather than selecting good-performing candidates retrospectively. Do not use outcome data from locked Fresh records.

## Pre-result source chronology gate

Each model forecast must include `source_received_at` as a timezone-aware timestamp. The evaluator rejects absent receipts, sources received after forecast generation, and sources received at or after the official deadline. This checks timestamp consistency only; the source's actual arrival and authenticity must be verified against trusted external receipts. No historical reconstruction or locked Fresh result access is permitted.

## Exploratory sample gate

Fewer than 30 eligible paired races result in `INSUFFICIENT_EVIDENCE` even when descriptive metrics are output. This is an operational floor, **not** a power calculation or a proof that 30 races suffice. No sample count alone can authorize promotion without independently audited first-seen evidence, pre-registered cohort and source receipts, permitted outcomes and paired performance validation. Comparing a model against itself is rejected.
