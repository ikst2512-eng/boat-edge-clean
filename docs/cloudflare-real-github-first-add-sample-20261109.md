# BOAT EDGE CLEAN — real GitHub native first-add sample (2026-11-09 JST)

**Evidence class: actual GitHub READ-ONLY connector observations, not mock data.**
**Scope: single same-race example `202611090203`. NOT a Cloudflare rescue / official T−12 certification.**
The evidence was read from GitHub's actual REST commit, contents/blob and comparison endpoints on 2026-11-09 JST. This document preserves the inspected object IDs and limits, not the raw original API response bytes or an authenticated Cloudflare event. PR #1697 remains Draft/unmerged; no main/Render/native Actions/Cloudflare deployment was modified.

## Same-race GitHub evidence

| Observed property | CLEAN | Four-mode |
|---|---|---|
| Native capture commit | `a4e7168f8af26e989d45df76746ae24b3fa5b690` | `ebe9b8ee18c34acda480a6d498c930c6c3b8b8be` |
| Git commit parent | `f657ff36ae27173a50adcab508f514eef15c18a6` | `a4e7168f8af26e989d45df76746ae24b3fa5b690` |
| Git commit committer time | `2026-11-09T01:31:49Z` (10:31:49 JST) | `2026-11-09T01:38:10Z` (10:38:10 JST) |
| Exact new path | `prospective_predictions/202611090203.json` | `four_mode_forecasts/202611090203.json` |
| GitHub commit-files status | `added` | `added` |
| Git blob SHA-1 (commit and contents API) | `506b4e24695bd31d7ddd7041f36bc37759d52888` | `41b367537e575f2dda48acc921c7831f2aed57ac` |
| Contents vs Git blob API bytes | identical (1,219 UTF-8 chars) | identical (5,627 UTF-8 chars) |
| Same path at immediate parent commit | HTTP 404 (not found) | HTTP 404 (not found) |
| Main ancestry | comparison `status:ahead`, `behind_by:0` | comparison `status:ahead`, `behind_by:0` |
| Immutable research state | `prospective_candidate`, `formal:false`, `validated:false` | `provisional`, `validated:false`, `formal` absent |
| Generated JST | `2026-11-09T10:31:48.770953+09:00` | `2026-11-09T10:38:07.270079+09:00` |
| Title received JST | `2026-11-09T10:31:48.645228+09:00` | `2026-11-09T10:38:06.908106+09:00` |
| Cards received JST | `2026-11-09T10:31:48.747225+09:00` | `2026-11-09T10:38:07.253625+09:00` |
| Source voting deadline JST | `2026-11-09T11:39:00+09:00` | `2026-11-09T11:39:00+09:00` |
| Derived T−12 JST | `2026-11-09T11:27:00+09:00` | `2026-11-09T11:27:00+09:00` |

Both records explicitly contain the same *reported* public pre-race input SHA-256 pair:
- `title`: `78849ddaa37cffd1c7f6744f1360201fd9d400958603a0ed6f7a730e062e89d7`
- `race_cards`: `b39627877a005fd5f3ecfe13040fc9c583454cc9ee207eba3195739a0bfd5e49`

This equality is **original JSON field consistency** and does not independently authenticate external public-source CSV bytes. Four-mode's original `beforeinfo` field reads `optional_not_in_snapshot`; neither original alone proves the required official beforeinfo/exhibition 6 boats or all 120 odds combinations.

### GitHub source links / reproducibility

- [CLEAN original addition](https://github.com/ikst2512-eng/boat-edge-clean/commit/a4e7168f8af26e989d45df76746ae24b3fa5b690)
- [Four-mode original addition](https://github.com/ikst2512-eng/boat-edge-clean/commit/ebe9b8ee18c34acda480a6d498c930c6c3b8b8be)
- [CLEAN exact original blob](https://github.com/ikst2512-eng/boat-edge-clean/blob/a4e7168f8af26e989d45df76746ae24b3fa5b690/prospective_predictions/202611090203.json)
- [Four-mode exact original blob](https://github.com/ikst2512-eng/boat-edge-clean/blob/ebe9b8ee18c34acda480a6d498c930c6c3b8b8be/four_mode_forecasts/202611090203.json)

Each run of this read-only audit inspected the REST **commit-files list with `status:added` and Git blob SHA**, the exact file content at that commit SHA, the same immutable blob by Git object SHA, the absence of that filename in the immediate parent, and `compare/<commit>...main` showing it as an ancestor of current main (at observation time). This is materially stronger than a synthetic manifest or a green capture CI alone, but only for the sampled archived paths.

### Formal evidence boundaries — all still NO-GO

1. **Not a Cloudflare rescue:** Neither commit is independently tied to a Cloudflare `workflow_dispatch` receipt, run ID or live Worker. These are existing native publisher archive additions.
2. **Commit time is NOT GitHub's first HTTP receipt time:** The time `commit.committer.date` is Git object metadata. This sample does not preserve a GitHub server-observed earliest arrival or authenticated transport proof. T−12 on-time server acceptance is **not formally established** even though source/commit metadata precedes 11:27.
3. **Not authoritative official source:** Public title and racer-card digests are present in both files; official pre-T−12 beforeinfo, 6 exhibitions, 120 odds and their independent receipts have not been read here.
4. **One sampled race ≠ all saved races:** Commit additions have many paths, but this document validates the exact pair above only. Duplicate/race-specific remote first-add across other files is not established by this sample.
5. **Cannot release cross-provider rescue:** Native CLEAN's pending queue can still be displaced by a new rescue `workflow_dispatch`, and Render does not share the Cloudflare-only research Durable Object. `CROSS_PROVIDER_DISPATCH_RELEASE_LOCKED=true` stays in place. Cloudflare Free live CPU/Cron remain unmeasured and formally recognized recovery count remains **0**.

**Owner handoff:** Independently fetch raw REST/HTTP responses with retained query timestamps and hashes, validate Git parent/tree/diff and original bytes for *each* target race, correlate the real native workflow run with the exact commit/first-add, then attach actual public/official source original receipts and GitHub-server observation evidence. Keep this current observation as a narrow but real provenance example, not a fabricated end-to-end forecast certification.


## Repeatable read-only REST verifier (Draft research)

The addition `cloudflare/remote_github_first_add_audit.mjs` and CLI `scripts/audit_github_real_first_add.mjs` can re-fetch this sample directly from **public GitHub REST**, using only GET requests (no PAT, POST, dispatch, git push, or workspace writes):

```sh
node scripts/audit_github_real_first_add.mjs clean 202611090203 a4e7168f8af26e989d45df76746ae24b3fa5b690
node scripts/audit_github_real_first_add.mjs four_mode 202611090203 ebe9b8ee18c34acda480a6d498c930c6c3b8b8be
```

The verifier requests exact commit metadata; its `files[]` entry with `status:"added"` and matching blob SHA; raw content at the commit via the Contents API; the same object via Git Blob API; the **parent commit's real Git root tree and the archive directory's nonrecursive Git subtree**; an independent **HTTP 404 for the exact same path at the immediate parent**; and ancestry from the target commit to current `main`. It refuses any incomplete (`truncated:true`) tree or unexpected tree SHA/type, so a 404 by itself is never enough. It calculates Git's SHA-1 over the *actual binary blob bytes* and the independent raw SHA-256, and validates the original record's race identity, source digests and local clock chronology. Every other GitHub API status, fabricated path or malformed blob fails closed. This is stronger than accepting a manually assembled JSON manifest.

The test suite uses **intercepted mock GET responses** to prove these failure gates without relying on public API availability during CI. The original GitHub connector direct-read checks above, however, were performed on *real* GitHub data. Both immediate parent root trees and archive subtrees were also retrieved directly through the GitHub connector: CLEAN parent root tree `450b17121b16207cdbf0678b0f41583d90919dc9`, archive subtree `9987fa5519f564d4be0eee35e831233748aa1312` (1,441 entries), and four-mode parent root tree `55bf150faf64dcf306147c109f7fa372ca55220a`, archive subtree `f42206863e92262a0ec082316df0b87c8114f872` (1,334 entries). Both `truncated:false`, with `202611090203.json` absent. These are real GitHub tree-object observations, not synthetic manifests. No claim is made that this CLI was executed live inside GitHub Actions or that the raw HTTP receipts were cryptographically signed. The tool outputs `github_remote_first_seen_timestamp_proven:false`, `native_run_id_independently_proven:false`, `cloudflare_rescue_dispatch_proven:false`, and `official_t_minus_12_proven:false` regardless of success.

The real observed commit-file lists for these two sample commits contained 107 and 104 entries respectively; no claim is made here about all paths being audited. Re-run with the network and current GitHub main available; if GitHub returns 403/rate limit or the sample is not an ancestor of main, the verifier refuses a passing result.


**2026-11-09 follow-up hardening:** The read-only verifier performs **8 GitHub GETs per race** (commit, file contents, Git blob, parent Git commit object, parent's root tree, parent's archive directory subtree when present, parent path contents, compare-to-main). GitHub's [official Git trees API](https://docs.github.com/en/rest/git/trees) specifies that `truncated:true` prevents exhaustive negative membership assertions; therefore the implementation requires explicit `truncated:false`. The true parent tree must resolve to the commit's immediate parent SHA and all matching archive-directory entries must be consistent. The source bytes must have canonical Base64 encoding (only CR/LF wrapping tolerated), a matching size, the actual Git SHA-1 object ID, and a matching separately fetched Blob response. These are code-level guards validated by **mocked** negative regression tests, not claims of live GitHub CLI execution or official race-source authenticity.

A previous output label mixed UTC time with the suffix `deadline_jst`; it has been corrected to return the literal original `+09:00` voting deadline. The T−12 output remains a generated +09:00 time based on the verified record. Never infer an authenticated GitHub server receipt from Git object's committer date.
