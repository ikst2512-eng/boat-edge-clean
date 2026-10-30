# Formal Fresh Git tree inventory: verified result (2026-10-30 JST)

## Successful run
- Workflow: https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/40950644845
- Git commit audited: `6415bb29ed589f3b599d149f9e63ef072e625140`
- Successful retry: unit-test SUCCESS, audit-evidence SUCCESS
- Artifact: `cross-model-audit-evidence`, GitHub artifact ID `12947558932`
- Artifact ZIP digest: `sha256:848f415eff3db1cbcf1277b49e76a54d7d40a1aa79d702eb616402d5c0c6ffef`
- Issue log: https://github.com/ikst2512-eng/boat-edge-clean/issues/329#issuecomment-6512968248

## Source tree results
- Matching race IDs: **440** (was 420 in earlier snapshot; tree advanced)
- Both sides contain readable forecast evidence: **29**
- Top10 comparisons completed: **29**
- Failed source fetches: **0**
- Legacy Git blob files under `data/formal_predictions/` and `data/formal/`: **0**

## Preservation interpretation
- The **two inspected formal prefixes contain no blobs in the audited Git tree**. No files in these prefixes can be migrated from that snapshot.
- This does **not** prove there are no formal Fresh receipts elsewhere, historical deleted Git files, GitHub Actions artifacts, external sources or other refs.
- The legacy `data/site_prediction_*` and `data/site_autopilot/v229_evidence/` paths remain **SITE_ONLY_NOT_FORMAL_FRESH**; do not rebrand them as formal records.
- Old V122 forecasts remain a different model from CLEAN; no migration or overwrite.
- Git history, current live workflows and old proof chain cannot be deleted merely because these two directories are empty.

## Next safe checks
1. Inventory alternate formal receipt/manifest paths on the complete tree (not only `data/formal_predictions/` and `data/formal/`).
2. Inspect historical first-add Git commits for any formerly deleted formal files, if relevant.
3. Verify old workflow dependencies and restoration before removing any proven-unused old paths.
4. Keep Issue #329 open until evidence-retention decision has a file-by-file source trail.
