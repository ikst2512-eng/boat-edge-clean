-- Proposed Cloudflare D1 research-only schema. NOT deployed.
-- A privileged D1 administrator can alter/drop the schema; the triggers
-- prevent ordinary application UPDATE/DELETE, not administrator tampering.
CREATE TABLE IF NOT EXISTS hole_pair_first_receipts (
    race_code TEXT PRIMARY KEY NOT NULL,
    candidate_sha256 TEXT NOT NULL,
    canonical_record TEXT NOT NULL,
    cutoff_utc TEXT NOT NULL,
    first_received_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (length(race_code) = 12),
    CHECK (length(candidate_sha256) = 64),
    CHECK (length(canonical_record) < 40000)
) STRICT;

CREATE TRIGGER IF NOT EXISTS hole_pair_first_receipts_no_update
BEFORE UPDATE ON hole_pair_first_receipts
BEGIN SELECT RAISE(ABORT, 'hole_pair_receipt_immutable_update'); END;

CREATE TRIGGER IF NOT EXISTS hole_pair_first_receipts_no_delete
BEFORE DELETE ON hole_pair_first_receipts
BEGIN SELECT RAISE(ABORT, 'hole_pair_receipt_immutable_delete'); END;
