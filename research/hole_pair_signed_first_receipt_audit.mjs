/**
 * Research-only Ed25519 authenticity check for a claimed first candidate receipt.
 * A mathematically valid signature proves ONLY that the supplied trusted key
 * signed these bytes. It never proves independent key custody, source timing,
 * actual first database insert, official T-12 or eligibility. No networking,
 * secret generation, signing, production scoring or deployment.
 */
import {createHash, createPublicKey, verify as edVerify} from 'node:crypto';
import {validateRecord} from './hole_pair_first_receipt_worker.mjs';

export const STATEMENT_SCHEMA = 'HOLE_PAIR_EXTERNAL_FIRST_RECEIPT_STATEMENT_V1';
export const ENVELOPE_SCHEMA = 'HOLE_PAIR_EXTERNAL_FIRST_RECEIPT_ENVELOPE_V1';
export const DOMAIN = 'BOAT_EDGE_CLEAN_HOLE_PAIR_RECEIPT_V1\n';
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const HEX64 = /^[a-f0-9]{64}$/;
const LABEL = /^[A-Za-z0-9._:-]{1,96}$/;
const KEYS = Object.freeze([
  'schema', 'witness_id', 'key_id', 'race_code', 'candidate_record_sha256',
  'first_accepted_at_utc_claim', 'declared_cutoff_utc', 'claimed_first_write',
  'immutable_receipt_id',
]);
const TRUST_KEYS = Object.freeze(['witness_id', 'key_id', 'public_key_pem', 'spki_sha256']);

function fail(message) { throw new Error(message); }
function object(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
function exact(x, keys) {
  return object(x) && Object.keys(x).length === keys.length &&
    keys.every(k => Object.hasOwn(x, k));
}
function canon(x) {
  if (Array.isArray(x)) return '[' + x.map(canon).join(',') + ']';
  if (object(x)) return '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canon(x[k])).join(',') + '}';
  if (typeof x === 'string' || x === null || typeof x === 'boolean' ||
      (typeof x === 'number' && Number.isFinite(x))) return JSON.stringify(x);
  return fail('untrusted_canonical_json_type');
}
export function statementBytes(statement) {
  return Buffer.from(DOMAIN + canon(statement) + '\n', 'utf8');
}
function utcClock(s) {
  if (typeof s !== 'string' || !UTC.test(s)) fail('untrusted_utc_receipt_clock');
  const ms = Date.parse(s);
  if (!Number.isFinite(ms) || new Date(ms).toISOString() !== s)
    fail('untrusted_utc_receipt_clock');
  return ms;
}
function signatureBytes(s) {
  if (typeof s !== 'string' || !/^[A-Za-z0-9+/]{86}==$/.test(s))
    fail('noncanonical_ed25519_signature');
  const b = Buffer.from(s, 'base64');
  if (b.length !== 64 || b.toString('base64') !== s)
    fail('noncanonical_ed25519_signature');
  return b;
}

export async function auditOne(record, envelope, trust) {
  // Reuse the exact existing pinned three-arm/Top5/10-ticket candidate contract.
  const candidate = await validateRecord(record);
  if (!exact(trust, TRUST_KEYS) || !LABEL.test(trust.witness_id ?? '') ||
      !LABEL.test(trust.key_id ?? '') || !HEX64.test(trust.spki_sha256 ?? '') ||
      typeof trust.public_key_pem !== 'string' || trust.public_key_pem.length > 2000)
    fail('external_witness_trust_anchor_missing_or_invalid');
  if (!exact(envelope, ['schema', 'statement', 'signature_b64']) ||
      envelope.schema !== ENVELOPE_SCHEMA || !exact(envelope.statement, KEYS))
    fail('unknown_or_forged_witness_envelope_fields');
  const s = envelope.statement;
  const digest = createHash('sha256').update(candidate.record_text).digest('hex');
  if (s.schema !== STATEMENT_SCHEMA || s.witness_id !== trust.witness_id ||
      s.key_id !== trust.key_id || s.race_code !== candidate.code ||
      s.candidate_record_sha256 !== digest ||
      s.declared_cutoff_utc !== candidate.cutoff_utc ||
      s.claimed_first_write !== true || !LABEL.test(s.immutable_receipt_id ?? ''))
    fail('signed_witness_identity_or_candidate_digest_mismatch');
  const first = utcClock(s.first_accepted_at_utc_claim);
  const finish = utcClock(candidate.finish_utc);
  const cutoff = utcClock(candidate.cutoff_utc);
  if (first <= finish + 1000 || first + 2000 >= cutoff)
    fail('signed_clock_claim_too_early_late_or_ambiguous');
  let pub;
  try { pub = createPublicKey(trust.public_key_pem); }
  catch { fail('invalid_out_of_band_witness_public_key'); }
  if (pub.asymmetricKeyType !== 'ed25519') fail('untrusted_witness_key_algorithm');
  const spki = pub.export({type:'spki', format:'der'});
  const actualFp = createHash('sha256').update(spki).digest('hex');
  if (actualFp !== trust.spki_sha256)
    fail('witness_key_fingerprint_not_pinned');
  const signature = signatureBytes(envelope.signature_b64);
  if (!edVerify(null, statementBytes(s), pub, signature))
    fail('signed_witness_attestation_invalid');
  return {
    schema:'HOLE_PAIR_EXTERNAL_SIGNATURE_READINESS_AUDIT_V1',
    race_code:candidate.code,
    candidate_record_sha256:digest,
    witness_id:s.witness_id,
    witness_key_id:s.key_id,
    witness_public_key_spki_sha256:actualFp,
    claimed_immutable_receipt_id:s.immutable_receipt_id,
    claimed_first_accepted_at_utc:s.first_accepted_at_utc_claim,
    ed25519_signature_valid_for_supplied_trust_anchor:true,
    // Neither the caller's key nor signed JSON is independent custody proof.
    independent_key_custody_verified:false,
    trusted_receiver_first_write_and_append_only_proven:false,
    accepted_time_externally_attested:false,
    official_t12_complete_verified:false,
    official_deadline_independently_verified:false,
    candidate_source_independently_verified:false,
    formally_eligible:false,
    formal:false,
    production_promotion_allowed:false,
    warning:'Ed25519 signature verifies under caller-supplied pinned key only; independent witness custody, trustworthy server time, first-write, and official T-12 are NOT established.',
  };
}

export async function auditBatch(records, envelopes, trust) {
  if (!Array.isArray(records) || records.length > 500 || !object(envelopes))
    fail('untrusted_witness_batch');
  const rows = [], seen = new Set();
  for (const record of records) {
    if (!object(record) || typeof record.race_code !== 'string' || seen.has(record.race_code))
      fail('duplicate_or_invalid_frozen_race');
    seen.add(record.race_code);
    const entries = envelopes[record.race_code];
    if (entries === undefined) {
      // Still validate a record even if receipt evidence is missing.
      const validated = await validateRecord(record);
      rows.push({race_code:validated.code, status:'no_signed_witness_attestation', formally_eligible:false});
      continue;
    }
    if (!Array.isArray(entries) || entries.length === 0 || entries.length > 20)
      fail('untrusted_witness_race_attestation_list');
    const verified = [];
    for (const item of entries) verified.push(await auditOne(record, item, trust));
    const ids = new Set(verified.map(x => x.claimed_immutable_receipt_id));
    const clock = new Set(verified.map(x => x.claimed_first_accepted_at_utc));
    const conflict = ids.size !== 1 || clock.size !== 1;
    rows.push({race_code:record.race_code,
      status:conflict ? 'signed_first_receipt_conflict_quarantined' :
        'signed_claim_consistent_not_independent_receipt',
      signed_claims_examined:entries.length,
      signed_claims_conflict:conflict,
      formally_eligible:false});
  }
  if (Object.keys(envelopes).some(code => !seen.has(code)))
    fail('orphan_witness_attestation');
  return {
    schema:'HOLE_PAIR_EXTERNAL_SIGNATURE_READINESS_BATCH_V1',
    examined:records.length,
    signed_claim_races:rows.filter(x => x.status === 'signed_claim_consistent_not_independent_receipt').length,
    quarantined_signed_claim_conflicts:rows.filter(x => x.signed_claims_conflict).length,
    missing_signed_claim_races:rows.filter(x => x.status === 'no_signed_witness_attestation').length,
    independent_first_receipt_verified:0,
    officially_qualified_t12:0,
    formally_eligible:0,
    formal:false,
    production_promotion_allowed:false,
    rows,
  };
}
