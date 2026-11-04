# P0 one-shot Git clone → originals ZIP: operator execution gate (2026-11-04 JST)

This entry consolidates prior 45-batch manifests into a **single optional local execution tool** that reads 5,578 original files from a **trusted local Git clone** of the legacy repository. It does **not** require editing old Git, Actions, current site, prediction data, or CLEAN's production code.

The tool `boat_edge_p0_one_shot_archive.py` plus frozen 4,143-race matrix are packaged in `boat_edge_p0_one_shot_archive_operator_20261104.zip` (SHA256 `d87ec2f1e6157d4cd48843845381c254ed8f729010b521e7d7956ac3e0c8dd97`, 335,831 bytes, ZIP CRC passed). The local operator README provides an explicit `gh repo clone` and a single guarded `python3 ... --execute` command.

**Important safety and provenance properties:**
- Source pinned to old Git commit `f38204105a979aa6ef5293d1b9cad854056faadd`, not moving branch HEAD.
- Fixed P0 plan checks **1,125 distinct races and 5,578 indexed original file paths**, with precisely 46 odds + 1 history historically not indexed; no synthetic replacements.
- Reads original bytes from `git show <pinned-ref>:<path>` and recomputes Git blob SHA1 locally; writes original bytes to a new ZIP only if pinned source blob matches.
- Reopens the resulting ZIP and verifies each archived entry's Git blob SHA1 + SHA256, retaining a manifest containing original paths and individual byte checksums.
- Refuses an already existing destination; default without `--execute` is dry-run. It cannot mark independent provider custody complete by itself.
- **6/6 synthetic local Git integration/regression tests passed**, including actual source ZIP write/readback, source hash mismatch refusal, destination overwrite refusal, invalid ref refusal, duplicate rejection, and dry run.
- The actual frozen matrix independently parsed as 1,125 P0 races, 5,578 indexed objects, 47 unindexed slots.

**Unresolved external dependency:** The model runtime failed outbound DNS when requesting both `api.github.com` and `raw.githubusercontent.com`, so no actual P0 source archive was built here. An **authorized and network-enabled operator** must use the tool on a trusted cloned old repository, inspect output, then separately copy the completed original-byte ZIP to an approved *independent* provider and download it back for full restoration SHA verification. The prior connector-to-Drive prediction transfer restriction is not overridden by this operator handoff; use an authorized channel.

Existing direct Git object checks: **469/5,578**, but new independent source-byte backup = **0**. Prior Kiryu 5R odds original remains the only independently read-back P0 original byte file. Previously backed up 412 results are P1/P2 (P0=0).

**DO NOT merge as license to retire. DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**