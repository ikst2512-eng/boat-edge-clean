# Research snapshot first-commit audit — 2026-10-26

**Research only; no formal Fresh unlock, scoring or results access.**

Evidence: [first-add commit 23d5a36d9fea82b3ef00a9ea708198d959b80d88](https://github.com/ikst2512-eng/boat-edge-clean/commit/23d5a36d9fea82b3ef00a9ea708198d959b80d88), commit timestamp `2026-10-26T01:06:31Z`.

Parsed the 135 added `research_snapshots/*.json` records from that commit patch (not all current-main file bytes):

| Check | Observed count |
| --- | ---: |
| Records in first-add commit | 135 |
| Unique names / race codes | 135 |
| First Git commit timestamp <= stored cutoff | 135 |
| Self-recorded forecast and both source receipt times <= stored cutoff | 135 |
| 10 distinct predictions | 135 |
| Records lacking `model_git_sha` | 135 |
| Records lacking `input_sha256` | 135 |

**Scope limitation:** The checks above use the *stored* `cutoff_jst`; they do not independently confirm each official deadline or source contents. Git commit metadata is supporting evidence, not a verified remote first-receipt timestamp. Direct comparison of the original parsed JSON with four selected current-main copies previously found matching data, but full 135 current-main byte-for-byte comparison remains incomplete. Neither historic dependency hashes nor original input bytes are recoverable from these fields alone. No official results were accessed or scored during this audit.

**Disposition:** 135 candidates remain **unscored / not yet fully provenance-verified**. The absence of provenance is not proof of tampering. Do not calculate empirical hit rates or confidence intervals using the 135 as scored races. Record model/source proof and independent result confirmation before scoring; never reconstruct these from outcomes or retroactively label old missing data as pre-race evidence.

**Audit code restriction:** `scripts/audit_research_outcomes.py` accepts externally supplied attestations and an approved manifest digest. Digest agreement alone does not prove independent reviewer identity or authenticity. Keep its output research-only and treat self-declared verification flags as untrusted until original receipts are separately authenticated.
