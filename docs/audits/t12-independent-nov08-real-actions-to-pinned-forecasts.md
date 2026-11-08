# 2026-11-08 ~21:34 JST — Live CI replay of actual Nov 5–8 official-source archive bytes against pinned original forecasts

**Result:** Real archived source/forecast chronology re-audited in GitHub Actions on Draft PR #1694. **Formal certification 0; formal accuracy denominator undefined.** Audit-only, no model, collector, cron, UI, Render, or main changes.

## Why this adds evidence beyond synthetic unit tests

The audit already had archived pair/frozen comparison fixtures and an independent strict raw-source ZIP parser, but they had not been composed into an automatic *real historical archive → Git pinned forecast* check.

New read-only scripts:
- `scripts/audit_t12_archived_pair_forecast_replay.py`: joins four fixed historic GitHub Actions artifact IDs (Nov 5, 6, 7, 8) with **originally frozen** `prospective_predictions/{race}.json` and `four_mode_forecasts/{race}.json` at exact unchanged main SHA `6b371040fd2fc4398bfa882e6557c333cc0800c8`, independently fetching their Git contents, checking each file's Git object SHA-1 against decoded source bytes, reading original generated_at with explicit JST and matching race identity. It never generates, overwrites, or submits a forecast.
- `scripts/audit_t12_extracted_artifact_replay.py`: GitHub Actions' official `actions/download-artifact@v4` downloads four actual historical artifacts by their fixed **run IDs and artifact names**. The audit independently checks the GitHub Actions metadata's artifact ID, name, workflow run, digest and expiry; reads all contained official beforeinfo/odds original bytes and manifests, verifies individual SHA256, source URL/race identity, 6-boat exhibition/ST, 120 unique odds and T−12 chronology by reusing `audit_t12_scheduled_pair_zip.replay` and its underlying independent official source auditor.

**Original ZIP qualification:** Direct REST `/actions/artifacts/{id}/zip` attempted in [run #42480476604](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42480476604) returned **HTTP 401** under the CI runner token and was intentionally classified as a failed audit, not a successful source. The fixed process uses the official extraction action, whose extracted original bytes are re-audited. A temporary ZIP is built locally to reuse the existing ZIP parser, but **the temporary ZIP's SHA256 is not the GitHub original ZIP's SHA256**. We match GitHub-authenticated artifact metadata to the original immutable artifact digest and explicitly output `original_artifact_zip_digest_rehashed_by_ci=false`; therefore **do not** claim end-to-end CI rehash of the original unmodified ZIP. Original archive ZIP digests were separately verified in a previous independent local investigation; this live CI adds the complete raw-source-to-frozen-Git-blob match.

## Verified exact-head CI

[Read-only audit CI #42480810605](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42480810605) on head `158b39cb626df6efa60280f77a9a72a3d3c6e083`:

- **109/109 regressions successful**, grouped 12 schedule, 23 frozen pair, 16 three-original model gap, 10 durable archive presence, 10 same-day join, 16 scheduled ZIP parser, 13 real replay orchestration, 9 extracted artifact integrity tests.
- **All four historic official Actions artifacts downloaded successfully by GitHub official action**.
- Exact real-data diagnostic: `four_archived_source_runs_replayed=4`, `source_pair_races=8`, `official_two_original_complete_races=3`, `matched_immutable_forecasts=6`, `forecasts_generated_after_sources=0`, `official_three_original_races=0`.
- Saved report `reports/historical_real_source_forecast_replay.json` in the CI audit artifact, alongside schedule, durable archive and same-day blocker inventories. `formal=false`, `t12_eligible=false`, `accuracy_scoring_allowed=false`, denominator null.

## Raw official pair positive cases / immutable forecast generation direction

| Race | Official pair archive | Original official last receipt | Immutable CLEAN generated | Immutable V2 generated | Newer than source? |
|---|---|---|---|---|---|
| 11/5 びわこ11R `202611051111` | [#41976534374](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/41976534374) | 14:50:58.419703 JST | 11:04:24.496897 | 11:15:10.119704 | **No / No** |
| 11/6 鳴門10R `202611061410` | [#42170457446](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42170457446) | 14:47:48.721444 JST | 10:15:39.642861 | 10:15:36.394911 | **No / No** |
| 11/8 江戸川9R `202611080309` | [#42450048245](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42450048245) | 14:15:48.378360 JST | 10:12:31.149675 | 10:17:12.313648 | **No / No** |

The Nov 7 [#42342115412](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42342115412) original-source pair failed; its two candidates are not treated as forecast-approved. No candidate from 11/5,6,7,8 had an archived third official racecard original from these paired ZIPs. The CI also confirmed the durable `research-t12-external-evidence` branch has no saved 11/8 official three-original day directory.

## What is still missing for a legitimate positive certification

**Collector/model owner ①:** Establish enough actual cron activation and error-free official **three-original same-race before-T−12** captures, archived with byte hashes and source timestamps. Generate a genuinely new model forecast strictly after the latest official receipt but before official T−12, and independently witness the actual model input byte consumption; frozen earlier forecasts cannot be backfilled. Preserve immutable initial GitHub remote acceptance evidence and final entry identity.

**Auditor:** Independently replay the new candidate's three source originals, consumed model-input chain, source→prediction chronology, first Git remote acceptance and final entry before any promotion. A GitHub `success` job with 0 eligible candidates remains a no-op, not a formal capture.

The real-data result strengthens the certainty of the existing decision but **does not** raise the production capture rate or formal certifications. Leave #1694 Draft and unmerged; never automatically integrate to main.
