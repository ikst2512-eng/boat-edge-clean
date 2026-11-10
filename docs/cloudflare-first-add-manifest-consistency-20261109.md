# First-add / original-source manifest consistency lab (2026-11-09 JST)

**Status: OFFLINE RESEARCH ONLY — NOT A REMOTE FIRST-ADD CERTIFICATE.** PR #1697 remains Draft. This audit does not fetch from GitHub/Cloudflare, authenticate an API response, deploy a Worker, alter production, or certify a forecast.

## Purpose and evidence hierarchy

An accepted GitHub workflow-dispatch response (HTTP 200 with run ID) does not identify an actual immutable newly added forecast. Likewise, a green run and a successful `git push` are not proof of the original forecast's first GitHub receipt or of official beforeinfo/exhibition/120-odds availability before T−12.

`cloudflare/local_first_add_evidence_lab.mjs` and `scripts/audit_cloudflare_first_add_manifest.mjs` consume **operator-assembled JSON evidence** and make **only internal consistency** checks across:
- exact expected repository `ikst2512-eng/boat-edge-clean`, branch `main`, known native capture workflow path, claimed completed successful GitHub run, and matching reported dispatch run ID if supplied;
- claimed 40-character commit and parent SHA, Japan-time commit date and claimed newly added paths;
- exact UTF-8 bytes of each *claimed original Git blob*, Git's canonical blob SHA-1 (`SHA1("blob <byte_length>\\0" + bytes)`), independent raw-byte SHA-256, unique archive filename and race identity (12 digits, venue 01–24, race 01–12);
- parsed immutable CLEAN / four-mode record fields, source receipt timestamps, generation chronology, research-only status and source-hash format.

**Different cutoff meanings matter:** CLEAN has `source_deadline_jst` and separately `cutoff_jst = source deadline - 12min`. Four-mode has `deadline_jst` as the actual voting deadline; `T−12 = deadline - 12min`, and the collector's extra generation safeguard is `generated_at_jst < deadline - 20min`. Treating the two `deadline_jst`/ `cutoff_jst` fields as interchangeable would accept false time evidence. The Git committer time must be after generation and before the relevant T−12 time, but this is still not a GitHub server first-seen timestamp.

### Offline operator command

```sh
node scripts/audit_cloudflare_first_add_manifest.mjs ./first-add-evidence.json
```

Result exit status 0 means only `local_content_consistency_pass:true` for the **supplied** source bytes/metadata; 1 is a contract mismatch, 2 is malformed/unreadable input. The CLI outputs the source input SHA-256 for later byte-for-byte comparison. It never sends requests or prints original raw blobs. The research output retains all the following flags **false**, unconditionally: `github_manifest_authenticity_independently_proven`, `git_first_add_parent_tree_independently_proven`, `remote_server_first_receipt_independently_proven`, `official_beforeinfo_six_boats_proven`, `odds_120_combinations_proven`, `official_t_minus_12_proven`, and `cross_provider_recovery_release_approved`.

### Required JSON schema

- `schema`: `BOAT_EDGE_FIRST_ADD_SOURCE_MANIFEST_LAB_V1`; `publisher`: `clean` or `four_mode`; `repository`: exact repository; `branch`: `main`.
- `github_run`: `id` (positive safe integer), `workflow_path` (exact native YAML), `event` (`schedule` / `workflow_dispatch`), `head_branch` (`main`), `status` (`completed`), `conclusion` (`success`). `reported_dispatch_run_id` is optional, but if present must exactly match a workflow-dispatch run ID.
- `commit`: `sha`, `parent_sha` (distinct lower-case 40-hex), `committed_at_jst` (offset-aware +09:00).
- `claimed_added_paths`: full claimed Git first-add path roster; `records`: one corresponding row per path, 1–150 records, unique names, `claimed_git_status: added`, `original_git_blob_utf8` (exact text, including trailing newline), `claimed_git_blob_sha1` and `claimed_raw_sha256`.

Do **not** fabricate or alter any fields to make the lab green: retrieve raw bytes and original API responses from the appropriate independent auditor and preserve them under their own immutable SHA. `claimed_git_status:"added"`, GitHub run metadata and `committed_at_jst` are merely manifest assertions until checked directly against the real remote commit parent/tree/diff and API response. A self-consistent manifest can be fully invented.

## Owner handoff and formal release conditions

The native publisher/repository auditor, outside this Cloudflare research PR, must independently fetch the GitHub run ID (correct event, main branch, workflow and outcome), server-side commit parent/tree, real added file list, and the corresponding blob bytes, then verify the exact first-add path and blob SHA. Also preserve real server observation time separately from committer time; a later observation is not necessarily first receipt. For each race, independently verify official beforeinfo, six exhibition entries, all 120 odds combinations, original timestamps and the correct T−12 cutoff in the same chain. Cross-provider duplicated dispatch and native CLEAN queue displacement still require separate publication-owner fixes.

**No inference of live completion:** This lab neither confirms a live Cloudflare Cron/CPU result nor proves any successful independent recovery. The release gate remains source-hard-locked, `CLOUDFLARE_DISPATCH_ENABLED="false"`, and production changes/auto-merge are prohibited.
