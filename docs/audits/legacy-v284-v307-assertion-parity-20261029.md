# Assertion-level comparison: legacy V284 and V307 against CLEAN (2026-10-29)

This compares actual test source, not similar workflow names. Read from legacy main `tests/test_boat_edge_v284_result_states.cjs` and `tests/test_boat_edge_v307_ui_ci.py`, and CLEAN main `tests/site-regression.cjs` and `.github/workflows/site-regression.yml`.

## V284 — result states

Legacy V284 source asserts five UI legend labels in order: 締切前固定, 🎯 検証済み的中, 検証済み不的中, 結果待ち, 検証対象外. It explicitly distinguishes pending from misses, checks CSS classes, verifies post-result provenance and numeric payouts, and disallows a fabricated purchase confirmation.

CLEAN existing regression executes actual `classifyPredictionMatch`, `isOfficialResultSource`, and `isVerifiedResult` from production `index.html`. It tests a confirmed result plus rejection of provisional status, mismatched race/date/source, invalid ranking, duplicated boats, nonnumeric/negative payouts and bad timestamps. It checks that per-mode hit history is derived from confirmed results and frozen forecast proofs, and that unverified hit/ROI rates are suppressed.

**Verified overlap:** both prevent treating unverified results as confirmed hits. **Not equivalent:** V284's five-label ordered legend, 'pending != miss' wording, V284 CSS, and the no-purchase-claim check are not established by these CLEAN regression assertions. CLEAN's different UI must be tested against its own five-state product requirements; do not transplant old DOM selectors.

## V307 — UI integration gate

Legacy V307 contract tests enforce a source-only PR gate with no schedule, workflow_run, manual dispatch, write permission, git push/commit, result unlock, or result/pay endpoints; it also requires particular old UI source tests and a formal 100-race lock check.

CLEAN `site-regression.yml` uses Node 22 to run `tests/site-regression.cjs`, uploads provenance and regression artifacts, and on PR runs a browser publish smoke test. CLEAN `mobile-smoke.yml` runs a production Render UI/health/input-validation browser check, but its browser job excludes PRs. CLEAN regression asserts racecard reads from CLEAN APIs and not old repo paths, the absence of false confirmation, source validity and guarded forecast scoring.

**Verified overlap:** site/UI regression execution and evidence traceability. **Not equivalent:** CLEAN site-regression workflow has an intentional `workflow_dispatch`, unlike V307, so its trigger policy cannot be copied. Read-only permissions, no writer commands, source-only formal lock, and old V307 mandatory tests require an explicit CLEAN-specific gate and runtime verification before any claim of replacement.

## Retirement decision

- V284: **KEEP**, partial source-level overlap with CLEAN's confirmed-result validator.
- V307: **KEEP**, partial workflow-level overlap with CLEAN regression/browser smoke.
- Remaining 15: **KEEP pending individual assertion-level comparison**.
- No old-site edits, no deletion authorization, no claims of full data/fixture parity.

## Completion criteria

For each old workflow map each asserted invariant to one of (a) a named CLEAN assertion and verified run, (b) intentionally not applicable with rationale, or (c) missing and requiring a CLEAN test. Require actual execution success on matching fixtures, provenance storage, rollback, and independent evidence checks. Names and single example fixtures cannot establish full equivalence.
