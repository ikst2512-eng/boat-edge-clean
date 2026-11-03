# 2026-11-04: downloaded cross-model evidence receipt and pinned-blob sample

This is an additive, read-only verification receipt for #708/#329. It does **not** attest to long-term independent backup of legacy forecast originals.

## Verified from actual downloaded artifact

- CLEAN workflow run: `41556670332`; jobs `unit-test` and `audit-evidence` both `completed/success`.
- Artifact: `cross-model-audit-evidence` ID `13194783484`; expiry `2026-12-03T01:06:26Z`.
- Downloaded ZIP byte SHA-256 calculated locally: `0823d71201fc51ddb9d08021a557f469bd4acbb2980205a0e916c1159aad7831`. **Matches GitHub artifact digest**.
- ZIP members successfully parsed: `crosswalk.json` (4,812,123 bytes) and `cross_model_audit.json` (1,379,549 bytes).
- Embedded immutable source tree SHA: legacy `f38204105a979aa6ef5293d1b9cad854056faadd`; CLEAN `eff4975851744a9851ce82383c79662b76496747`.
- Embedded race count: matched `1046`, legacy-only `3097`, CLEAN-only `147`; comparison `108`, non-comparable `938`, unresolved `0`.
- Embedded prefix counts (as of that tree, **not current live count**): legacy `data/raw/` 9814, `data/site_odds/` 2642, `data/site_prediction_audit/` 1282, `data/site_prediction_history/` 1277, `data/site_prediction_snapshots/` 2270, `data/site_results/` 4137; CLEAN `confirmed_results/` 1034, `four_mode_forecasts/` 749, `four_mode_performance/` 400, `prospective_predictions/` 762.
- `formal_artifact_count=0` is a finding **only for the explicitly inventoried formal prefixes**; it must not be extrapolated to all historic Fresh data.
- Artifact declares `delete_authorized=false`, `copy_authorized=false`, and `workflow_dependency_graph_verified=false`.

## Direct GitHub source spot-check (pinned legacy tree)

Race `202610270101` (2026-10-27 Kiryu 1R) direct-fetch content and blob SHA:

| Source | Actual GitHub blob SHA | Audit ZIP blob SHA | Match |
| --- | --- | --- | --- |
| `data/site_prediction_audit/20261027-01-01.json` | `71b428412efda52d96321c2cbdbb155f729fbaed` | same | YES |
| `data/site_prediction_history/20261027-01-01.json` | `64f9e64cdd045b3103179d80bdb94059857bf70e` | same | YES |
| `data/site_prediction_snapshots/20261027-01-01.json` | `034910dbb2c331a3925d13651d58126bc4e5ed3d` | same | YES |

The content declares model `SITE_REFERENCE_V122`, `FINAL_15M`, and `scope=SITE_ONLY_NOT_FORMAL_FRESH` in the audit. The embedded JSON `first_saved_at` is **not** a GitHub first-add attestation; no historical Git first-add search was performed for this spot-check. Original file hashes are visible in the audit artifact, but this receipt's 3/3 result is **Git blob ID comparison**, not independent bytewise SHA256 rehash of each restored file.

## Next gate

Preserve **actual source bytes**, Git first-add chronology, source/odds/result evidence, and per-race SHA256 in independent durable storage, then read back and compare. Until that is independently demonstrated, keep old collectors, publisher, files and repository unchanged.

**NO DELETE / NO STOP / NO IMPORT / NO PRODUCTION CHANGE.**
