# 2026-11-09 16:55 JST — two NEW official source pairs, four unchanged early forecasts

**Independent research audit only (Draft #1694). Formal T−12 certificates: 0; formal accuracy denominator: undefined.** Source collection, model, scheduling, main, forecasts, Render and UI are not modified.

## Verified official source files from Nov 9 schedule run

The actual [schedule-run #42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743) started 2026-11-09 14:26 JST, under `.github/workflows/research-live-preview-evidence.yml`. Its archived original artifact [#13652131213](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743/artifacts/13652131213) has advertised and locally rehashed *original Actions ZIP* SHA256:

`99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451`.

The downloaded ZIP passed `ZipFile.testzip()`; **4/4 official beforeinfo/odds originals** have matching individual `manifest.json` SHA256 and exact source-byte sizes. The archive's own `OFFICIAL_JOINT_BATCH` statement says `complete_pairs_before_t12=2`, but **the success statement alone was not used as proof**. The source originals were replayed independently again by [PR audit CI #42582365407](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42582365407), using the source-byte re-auditor and verified GitHub artifact metadata.

| Exact race code | Place | Official deadline | Official T−12 | beforeinfo original received (JST) | 120-way official odds original received (JST) | Replayed content |
|---|---|---|---|---|---|---|
| `202611091710` | 宮島10R | 14:40 | **14:28:00** | 14:26:32.711772 | **14:26:41.921482** | six valid exhibition/start rows + 120 unique odds; pair complete |
| `202611091110` | びわこ10R | 14:42 | **14:30:00** | 14:26:50.194266 | **14:26:59.498535** | six valid exhibition/start rows + 120 unique odds; pair complete |

The official two-original source chain is complete for these two selected races at T−12, but **official racelist original = absent from this pair archive**, final confirmed six-entry lineup = unverified, and model inputs are not independently replayed. No source-only success implies a valid prediction.

## Four frozen forecasts from pinned unchanged GitHub main snapshot

Read-only pinned commit: `a77c905893d7412dc99e68cabd2091bd579cc9bf`. The [CI #42582365407](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42582365407) fetched the four remote original JSON Git blobs with validated remote Git blob SHA and SHA256; no forecast was regenerated.

| Race | Frozen forecast | Original creation (JST) | Last official original (JST) | Source receipt AFTER forecast by |
|---|---|---|---|---:|
| 宮島10R | CLEAN `prospective_predictions/202611091710.json` | 10:31:48.770953 | 14:26:41.921482 | **14,093.151s** |
| 宮島10R | four-mode `four_mode_forecasts/202611091710.json` | 10:38:08.070980 | 14:26:41.921482 | **13,713.851s** |
| びわこ10R | CLEAN `prospective_predictions/202611091110.json` | 10:31:48.770953 | 14:26:59.498535 | **14,110.728s** |
| びわこ10R | four-mode `four_mode_forecasts/202611091110.json` | 10:38:07.795737 | 14:26:59.498535 | **13,731.703s** |

CLEAN `input_source_kind=public_pre_race_csv`; four-mode `beforeinfo=optional_not_in_snapshot`. These earlier frozen predictions **cannot retroactively consume** the later official source originals. No new post-source forecast has been identified in this bounded replay. Remote Git *existence at pinned commit* does not independently establish *first GitHub remote acceptance*.

## New automated audit (not a fabricated example)

Added `scripts/audit_t12_nov09_real_pair_forecast_replay.py` and **10 new fail-closed tests** at `tests/test_audit_t12_nov09_real_pair_forecast_replay.py`; these explicitly require same-race original-byte reinspection, source manifest/URL/6-boat/120 odds, T−12 chronology, exact immutable forecast blob and independent nonformal flags. Updated read-only PR workflow to use authenticated `actions/download-artifact@v4`, verify GitHub metadata digest, replay **original source bytes extracted from artifact** and compare forecasts pinned at exact Git commit. **The CI does not claim to recompute the original Actions ZIP digest from the extracted files.** That separate original ZIP hash was rechecked in the operator's analysis container.

[Exact code-head PR run #42582365407](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42582365407): **132/132 audit regression tests PASS**, GitHub actual raw original reinspection and all four remote forecast lookups successful. It published:

- `reports/official_t12_nov09_source_vs_forecast.json` with **2 verified official two-source pairs, 4 pinned forecast files, 0 forecasts generated after the sources, formal=false**;
- Current racing-day Nov 9 schedule snapshot at **16:55:56 JST**: **1** collector `event=schedule` creation, **96** elapsed nominal cron slots (09:00–16:55), **1.04% count ratio**. This is not proof of 95 failed HTTP requests, exactly missed cron slots, or scheduler root cause.
- Official three-original research Git branch `research-t12-external-evidence`, immutable SHA `d0ed89f146dff117021c2bc042b20259d6715515`, still has **no Nov 9 directory**. This is a limited branch inventory, not an absence claim for all other Actions artifacts.

The older 14:23 JST snapshot's zero collector run was correct **as of that earlier time**; the 14:26 scheduled run is newly observed after it. Do not conflate the two observation times.

## Owner handoff without modifying collection

**① official capture owner:** Separate sparse scheduled invocations from successful official two-original HTTP captures. The same-race Miyajima10/Biwako10 positive source receipts prove the official beforeinfo and 120-way odds paths can work within T−12. Urgently preserve the *third official racelist original*, and collect a **new** immutable model forecast strictly after the last source receipt and before T−12 on a future race; prove actual consumed original inputs. Do not backdate the 10:31/10:38 frozen forecasts.

**Independent audit owner:** Re-audit exact remote Git original triad and forecast model consumption, an independently attestable first Git remote acceptance and final entries; do not compute formal success rate until the valid denominator exists.

**Keep PR #1694 Draft; no main automatic merge or production promotion.**
