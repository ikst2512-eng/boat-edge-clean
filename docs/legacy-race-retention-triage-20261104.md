# Legacy race-granular retention triage — 2026-11-04 JST

**Read-only evidence analysis for #708 and #329.** Derived from the already-downloaded GitHub Actions `cross-model-audit-evidence` ZIP, run `41556670332`, artifact `13194783484`. Immutable legacy tree `f38204105a979aa6ef5293d1b9cad854056faadd`, CLEAN tree `eff4975851744a9851ce82383c79662b76496747`. No workflow, model, site, raw original or production data was changed.

## Race-level risk classification

| Cohort | Races | Priority / action |
| --- | ---: | --- |
| Legacy-only ID with original `site_prediction_snapshots` | **1125** | **P0**: protect original + audit/history, Git first-add evidence, input odds/source, settlement; no import to CLEAN model |
| Shared ID with legacy original `site_prediction_snapshots` | **156** | **P1**: keep separate old/new model provenance; never conflate same race ID with equivalent forecasts |
| Other legacy race IDs containing result/odds, no prediction snapshot under inventoried prefix | **2862** | **P2**: assess source/result value and external dependencies before retention decisions |
| **Distinct legacy race IDs in source crosswalk** | **4143** | All remain `DELETE_BLOCKED` |

### Source prefix presence in legacy-only race-ID cohort (3097 races)

- `data/site_prediction_snapshots/`: 1125
- `data/site_prediction_audit/`: 1125
- `data/site_prediction_history/`: 1124
- `data/site_odds/`: 2204
- `data/site_results/`: 3096

These are **per-race presence counts** and do not prove actual byte backups or forecast validity. `legacy_only` is relative to CLEAN's *recorded race IDs at that pinned tree*, not proof that no equivalent data is stored by another path, or that all 3097 contain predictions. Also note that 1125 snapshot races but 1124 history races require specific review of the one missing history association, with no repair/overwrite of originals.

### Full local indexing receipt

An off-repository, read-only CSV of **4143 distinct race IDs** was generated from the ZIP (not committed to the source repo): `boat_edge_legacy_retention_race_matrix_20261104.csv` (1,629,007 bytes), SHA256 `49d00beb719dd3efe45e5dd659ff5075309ac41f14147ef10cc9c2840deabb67`. Each record includes source Git tree SHAs, race cohort, P0/P1/P2, observed legacy file paths and Git blob SHA1, with all independent-backup, first-Git-add and restored-SHA256 flags explicitly set to `UNVERIFIED`.

The CSV is a *pointer/index*, **not** original source bytes, full backup, first-add proof, or approved retention policy. Existing 30-day Actions ZIP expiry remains a blocker. Keep this report small to avoid coupling the production code or CI to a temporary inventory.

## Acceptance for P0 before old site is retired

1. Fetch every required original at the pinned legacy Git commit (or explicitly document missing sources), preserve exact bytes plus Git blob SHA and SHA256, model, source time and first Git-add trace.
2. Retain the exact originals in **independent non-expiring storage**, reload from that storage, compare SHA256, and confirm the prediction-to-odds-to-result links.
3. Isolate `SITE_ONLY_NOT_FORMAL_FRESH` from formal Fresh and CLEAN research candidates; no automatic import/scoring eligibility.
4. Review old workflow caller/event/writer/consumer graph, public URLs and rollback readiness before **any** workflow stop. UI/Render and prediction owners continue independently.

**Decision: `DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED`**. This document is not authorization for a halt, archive, deletion or migration of prediction contents.
