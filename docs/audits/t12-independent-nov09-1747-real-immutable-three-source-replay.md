# 2026-11-09 17:47 JST — immutable Git source triple actually re-audited

**Purpose:** separate *presence of three official original files* from *complete six-boat exhibition source content*. Read-only T−12 research audit in Draft PR #1694. **Formal certifications 0; denominator for formal accuracy undefined.**

## Directly observed persisted source

The dedicated `research-t12-external-evidence` branch is pinned to commit `d0ed89f146dff117021c2bc042b20259d6715515`. Its Git tree includes exactly one known date directory, `external_three_t12/20261103`, with one race `202611030112` (**桐生12R**) and one actual observation `ext20261103T08003263231e6e`; there were no 11/08 or 11/09 date directories at the verification snapshot. The observer's declared report is *not used on its own* to claim success.

The independent [real GitHub Actions audit #42588424200](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42588424200) used the repository's existing `scripts.reaudit_external_three_t12.reaudit_published` to download the **six individual original and manifest Git blobs at the exact commit**, verify Git blob SHA1, independently check SHA256 and file length for each original, replay the actual official racelist + beforeinfo + 120-way odds contents with `audit_three_originals`, and then compare the semantic result against the originally published research report. Any missing/altered original or mismatch fails the audit; it never synthesizes exhibition rows.

### Raw replay result

| Requirement | Independently replayed result |
|---|---|
| Race | `202611030112`, 桐生12R |
| Persisted original/source files | **3 originals + 3 manifests, all Git blob/manifest hashes verified** |
| Official racelist | **6 registration identities verified**, agreed with beforeinfo |
| Official beforeinfo | 6 unique boat identity rows, **0/6 valid exhibition times**, **0/6 tilt**, **0/6 start-exhibition/ST rows**, **0/6 mapped exhibition courses** |
| Official odds3t original | **120/120 unique combinations** |
| Official T−12 cutoff | **2026-11-03 20:19:00 JST** |
| Last self-recorded source HTTP receipt | **2026-11-03 17:00:59.946462 JST** |
| Self-recorded source-receipt margin to T−12 | **11,880.054 seconds (3h18m)**, *not an independently observed remote-first-acceptance claim* |
| Three-source research content completeness | **false** (four missing components) |
| Qualified 3-source candidate from this observation | **0** |
| Any verified post-source, before-T−12 forecast | **none from this triple replay** |
| Formal T−12 certification | **0** |

**Specific diagnostic:** this saved observation was collected at ~17:00 JST, while official deadline was 20:31 JST. It captured the official racelist, bare pre-race six-entry beforeinfo and complete odds *hours before* the cutoff; its beforeinfo was not yet the six-boat exhibition data needed to produce a T−12 input. Thus the mere presence of all three official filenames says nothing about the actual exhibition gate. The timestamp itself is an archived request/receipt field, not a second-party verified time.

By contrast, real Nov 9 source ZIP [run #42567310743](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42567310743) had two timely 6/6-exhibition + 120 odds source pairs and an independently checked GitHub artifact server publication at **14:27 JST** before their official T−12 cutoffs, but these ZIPs do **not** include the third official racelist original, and their existing CLEAN/V2 forecasts were frozen hours earlier. **Do not combine the Nov 3 racelist with Nov 9 exhibition/odds across different races or dates.**

## Audit-only implementation and successful CI

New reusable read-only command `scripts/audit_t12_saved_three_original_replay.py` accepts `--repo --git-commit --race-code --observation-id --output`, runs independent pinned Git original replay, calculates the component/chronology classification from re-audited results, and always reports `formal=false`, `t12_eligible=false`, `forecast_usable=false`, `accuracy_scoring_allowed=false`. New `tests/test_audit_t12_saved_three_original_replay.py` adds **11 fail-closed tests** for tampering, identity, missing 6/6 rows, no valid model lineage, source timestamp conflicts and false certifications.

The GitHub PR workflow now executes the command against the **actual Nov 3 fixed evidence commit**, checks that the four observed missing components are exactly `exhibition_six_courses`, `exhibition_times_six`, `tilt_six`, `start_exhibition_six`, and saves `reports/official_t12_nov03_pinned_three_originals.json` alongside the current Nov 9 source-vs-prediction/source-archive-server-time reports.

[Exact-head CI #42588424200](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42588424200): **success, 167/167 unit tests** (prior 156 + 11), **real remote pinned triple original replay success**, Nov 5–8 ZIP replay and Nov 9 ZIP+forecast replay success, Nov 9 archive-server-time replay success. The distinct CLEAN prospective accuracy-check workflow remains a separately failing validation and has not been claimed green.

## Next external prerequisite, owner ①

A future **single race** must have all three original sources: official racelist (matching six racer registrations), official beforeinfo **after exhibition becomes complete but before T−12**, and original 120-combination odds, each immutable and independently replayable. Then generate a **new** official-sourced frozen forecast *strictly after* all three source receipts and *before* official T−12; prove original input consumption independent of a forecast's self-declared hashes; independently attest **first forecast GitHub remote acceptance** and final entry. Only then reconsider formal scoring. Existing early CSV forecasts cannot be upgraded retroactively.

**No changes to main, production source collection, scheduling, prediction engine, UI or Render. Draft PR #1694 remains unmerged.**
