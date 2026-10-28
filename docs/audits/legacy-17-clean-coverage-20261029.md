# Legacy 17: CLEAN verification coverage matrix (2026-10-29)

Evidence scope: old repo main YAML read for 17 workflows in PR #204; CLEAN main workflow inventory and direct review of `site-regression.yml`, `mobile-smoke.yml`, and `fresh-prospective-capture.yml`. This is **a scoped first-pass gap assessment**, not proof that matching test implementations are absent elsewhere in CLEAN.

| Legacy workflow | Safety behavior / tests mentioned in old workflow | CLEAN observation | Judgment |
|---|---|---|---|
| v278-guarded-ui-queue | monotonic guarded task queue, no invented completion | CLEAN general regression exists; exact guard not verified | GAP / keep |
| v279-relative-weights | relative-weight labels and formal status lock | CLEAN site regression exists; identical assertions not verified | GAP / keep |
| v281-selected-race | source evidence for selected race, no fabricated timestamps | CLEAN page regression exists; same provenance assertions not verified | GAP / keep |
| v282-exhibition-evidence | all six boats, source/third-party separation | CLEAN mobile smoke exists; six-boat assertion equivalence not verified | GAP / keep |
| v283-claim-safety | autopilot claim wording and formal lock | No equivalent formally verified | GAP / keep |
| v284-results-states | five verified result state labels and provenance | CLEAN result-collection workflow present; state parity unverified | GAP / keep |
| v286-retire-legacy-bootstrap | old installer rollback prevention and frozen ordering | Legacy-specific guard; no replacement verified | LEGACY-SPECIFIC / keep |
| v287-six-boat-beforeinfo | completeness and urgent beforeinfo retry | CLEAN independent data workflows exist, logic parity unverified | GAP / keep |
| v288-official-start-html | official exhibition HTML parsing | CLEAN odds parser regression exists, but different semantics | GAP / keep |
| v289-official-source-visibility | six-boat official source visibility, no fictitious data | CLEAN UI workflows exist; exact guard unverified | GAP / keep |
| v290-missing-freeze-funnel | source gap versus scheduler window, frozen provenance | CLEAN prospective workflows exist; exact diagnostics unverified | GAP / keep |
| v291-freeze-funnel-mobile | missing freeze evidence on mobile | CLEAN mobile smoke exists; exact freeze evidence assertions unverified | GAP / keep |
| v292-source-wake-safety | trusted source can wake immutable freeze | CLEAN Fresh candidate capture uses distinct repository_dispatch guard; not equivalent | GAP / keep |
| v295-retry-evidence | pre-result retry proposal evidence | CLEAN prospective flows exist; retry ledger parity unverified | GAP / keep |
| v296-retry-pair-integrity | retry source-pair integrity | CLEAN prospective flows exist; pair integrity parity unverified | GAP / keep |
| v302-v254-regression | formal empty fixture regression; git provenance | CLEAN general regression exists; fixture parity unverified | GAP / keep |
| v307-ui-integration-gate | UI-only integration regression, no data mutation | CLEAN site-regression and mobile-smoke cover some general UI checks, not a proven supersession | PARTIAL OVERLAP / keep |

## Findings
- 17/17 old workflow YAMLs have `push` and `pull_request` triggers with path filters (PR #204).
- CLEAN has its own `site-regression.yml` (Node.js 22, stored fixtures, artifact provenance), and `mobile-smoke.yml` (Render production browser check, health and validation), which are *not* by themselves proof of identical protection.
- CLEAN `fresh-prospective-capture.yml` has cutoff and receipt checks, but this does not prove equivalence to legacy freeze/retry controls.
- **No deletion eligibility established**; no old repository modifications.
- This matrix uses observed workflow wiring and labels. To clear a row, compare assertion-by-assertion in source tests, demonstrate actual CLEAN test pass on same fixtures, confirm old execution history and immutable evidence, and document rollback.

## Immediate next verification
1. Compare `tests/site-regression.cjs` assertion coverage with V307 and relevant old UI test files; add CLEAN fixture tests only where CLEAN actually needs the same invariants.
2. Compare six-boat source proof and beforeinfo parser assertions against CLEAN feed and forecast tests.
3. Map freeze/retry provenance and official Fresh immutability independently; do not collapse the different data pipelines into a claimed equivalent.
4. Audit existing CLEAN audit workflows for duplication before adding more scheduled jobs.
