# 2026-11-09 17:36 JST — independent GitHub server-origin T−12 source archive timing

**Read-only independent audit only.** Draft PR #1694 remains unmerged. No modifications to collectors, source HTTP, model, production cron, Render, UI, historical forecasts or main. **Formal T−12: 0; formal accuracy denominator undefined.**

## New bounded finding: two original-pair ZIP observations uploaded before their T−12 cutoff

Independent Nov 9 replay had already verified four original official source files (two `beforeinfo`, two odds3t originals), six complete exhibitions/start rows and 120 unique trifecta combinations for two exact races in [GitHub source run #42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743), artifact [#13652131213](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743/artifacts/13652131213).

An **additional, different timestamp source** is now checked. Authenticated GitHub REST returned:

- Source-run server `created_at` and `run_started_at`: **2026-11-09 05:26:15 UTC** = 14:26:15 JST.
- Archive artifact server `created_at` **and** `updated_at`: **2026-11-09 05:27:00 UTC** = 14:27:00 JST, after the last source's self-recorded receipt.
- Source-run server `updated_at`: **2026-11-09 05:27:04 UTC** = 14:27:04 JST.
- The source archive artifact was attached to that same actual `event=schedule` workflow on `main`, with run/head SHA consistency. `expired=false`, exact known artifact ID/name, nonzero size, exact source ZIP digest from authenticated GitHub metadata `sha256:99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451`.
- The original GitHub ZIP hash was separately verified in operator artifact analysis, **not** reconstructed by the new GitHub CI. The CI uses independently reaudited extracted original source files and the GitHub artifact metadata digest.

| Official-source original | Official T−12 cutoff JST | GitHub artifact updated JST | Server timestamp margin to cutoff | New research-only archive-time gate |
|---|---|---|---:|---|
| 宮島10R `202611091710` | 14:28:00 | 14:27:00 | **60 seconds** | Positive |
| びわこ10R `202611091110` | 14:30:00 | 14:27:00 | **180 seconds** | Positive |

The independent source ZIP remote **archive-timing** gate is positive **2/2** using server timestamps, while official **3-source** original coverage is **0/2**, a forecast actually generated after the original-source receipts is **0/4**, independent model input consumption **0**, and independently attested first forecast Git remote receipt **0**. A GitHub Actions artifact server `updated_at` is a distinct time observation: **do not call it the first receipt of a forecast, proof of original HTTP receipt truth, or proof that the model read the source bytes**.

The new audit uses one-second-positive margin because GitHub server timestamps are reported in whole seconds and it refuses an artifact updated exactly at the T−12 deadline. It fail-closes on wrong artifact/run/digest/expired state, workflow event `workflow_dispatch` substituted for schedule, source timing reversed, wrong racing day, omitted source bytes replay, a false model-lineage claim, or a truthy formal certification.

## Code and real CI evidence

Added:
- `scripts/audit_t12_remote_artifact_publication.py` — authentic GitHub artifact **and** run REST readback; validates raw replay report and published source archive chronology.
- `tests/test_audit_t12_remote_artifact_publication.py` — **12 bounded tests** including forged metadata/timestamps, cutoff equality, source integrity and formal fail-closed gates.
- `.github/workflows/audit-official-pair-schedule-continuity.yml` — runs tests and the actual Nov 9 remote metadata audit after immutable ZIP-source-vs-forecast replay; uploads `reports/official_t12_nov09_remote_archive_time.json`.

Exact code-head [read-only CI #42587061589](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42587061589) on `f60f13a34e7ddeba60b6349912e190f06a0af173`: **156/156 audit unit tests pass** (existing 144 plus 12), and the real authenticated GitHub source archive observation returned `server_timestamp_artifact_archive_before_t12_races=2`, `formal=false`, `new_formal_certifications=0`, `formal_accuracy_denominator=null`. The original replay of actual Nov 9 source bytes and four GitHub-pinned CLEAN/V2 forecasts also passed as upstream CI steps.

Separate live Nov 9 observation at **17:36 JST**: one collector `event=schedule` creation within **104 elapsed nominal five-minute slots** (0.96% creation-count ratio), no Nov 9 race directory in `research-t12-external-evidence` at immutable SHA `d0ed89f146dff117021c2bc042b20259d6715515`. This is a count, **not** 103 proven failed HTTP requests or exactly skipped cron slots. Earlier 16:55 evidence had 1/96; the clock-dependent denominator must always be stated.

## Direct next action for collector/forecast owner ①

The bounded **source-archive server-time** subgate is attainable. Preserve it while completing the still-blocking conditions **on the same newly observed future race**: official *racelist* original alongside official six-boat beforeinfo and 120-way odds, a new immutable prediction generated *after* the final original was obtained and *before* official T−12, independently replayed actual model consumption, independent first **forecast** GitHub remote acceptance and final entries. Do **not** retrospectively change the 10:31/10:38 CLEAN/V2 forecasts. Owner① should separately investigate the cross-workflow sparse scheduling pattern and avoid treating any green zero-candidate execution as a source capture.

No formal scoring or production release is authorized by this artifact-time audit. #1694 remains Draft, unmerged; independent review required.
