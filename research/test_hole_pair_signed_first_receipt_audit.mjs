/** Synthetic Ed25519 signatures only, with ephemeral Node-generated keys. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash, generateKeyPairSync, sign} from 'node:crypto';
import {auditOne, auditBatch, auditAcrossBatches, statementBytes, STATEMENT_SCHEMA, ENVELOPE_SCHEMA} from './hole_pair_signed_first_receipt_audit.mjs';
import {canonicalRecord} from './hole_pair_first_receipt_worker.mjs';

const METHOD='ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb';
const BLOBS={
  'hole_third_choice_research.py':'579edc1ae846489d447307fbf03b35fc7d4c09b9',
  'hole_pair_diversification_research.py':'56f06c10f6d07e03b2e37624ecf57dc6de7d8748',
  'hole_top5_safe_bundle_research.py':'a43f53d898ac73829e7f2b24f81624d69d26d74a',
  'hole_pair_third_bundle_research.py':'88c4ed506588a24bb593d104b5d0f59c7502d73a',
};
const PICKS=['1-2-3','1-2-4','1-3-2','1-3-4','2-1-3','2-1-4','1-4-2','1-4-3','2-3-1','2-3-4'];
const hash=x=>createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':
  x && typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
function candidate(code='202611090101'){
  const choices={baseline:[...PICKS],same_pair_two_thirds:[...PICKS],two_pairs_one_third:[...PICKS]};
  return {
    schema:'HOLE_PAIR_FUTURE_FREEZE_V1',status:'locally_frozen_unverified',race_code:code,
    method:'HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1',method_source_sha256:METHOD,
    model_version:'CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED',
    source_sha256:'a'.repeat(64),source_git_blob_sha1:'b'.repeat(40),
    locked_selector_git_blobs:{...BLOBS},candidates:choices,candidates_sha256:hash(canonical(choices)),
    local_start_jst:'2026-11-09T10:50:00+09:00',local_finish_jst:'2026-11-09T10:51:00+09:00',
    t_minus_12_jst:'2026-11-09T11:00:00+09:00',deadline_jst:'2026-11-09T11:12:00+09:00',
    formal:false,prospective_validation:false,independent_first_receipt_verified:false,
    production_forecast_changed:false,
  };
}
function witness(){
  const {privateKey, publicKey}=generateKeyPairSync('ed25519');
  const public_key_pem=publicKey.export({type:'spki',format:'pem'});
  const spki_sha256=hash(publicKey.export({type:'spki',format:'der'}));
  return {privateKey,trust:{witness_id:'test-external-receiver',key_id:'ephemeral-20261109',
    public_key_pem,spki_sha256}};
}
function envelope(record,w,overrides={}){
  const statement={
    schema:STATEMENT_SCHEMA,
    witness_id:w.trust.witness_id,key_id:w.trust.key_id,
    race_code:record.race_code,candidate_record_sha256:hash(canonicalRecord(record)),
    first_accepted_at_utc_claim:'2026-11-09T01:55:00.000Z',
    declared_cutoff_utc:'2026-11-09T02:00:00.000Z',
    claimed_first_write:true,immutable_receipt_id:'test-receipt-0001',
    ...overrides,
  };
  return {schema:ENVELOPE_SCHEMA,statement,
    signature_b64:sign(null,statementBytes(statement),w.privateKey).toString('base64')};
}

test('valid Ed25519 under ephemeral key proves ONLY supplied-key signature, never formal',async()=>{
  const c=candidate(),w=witness(),a=await auditOne(c,envelope(c,w),w.trust);
  assert.equal(a.ed25519_signature_valid_for_supplied_trust_anchor,true);
  for(const field of ['independent_key_custody_verified','trusted_receiver_first_write_and_append_only_proven',
    'accepted_time_externally_attested','official_t12_complete_verified','formally_eligible',
    'formal','production_promotion_allowed'])assert.equal(a[field],false,field);
});
test('signature binds exact candidate bytes and rejects changed tickets/timestamp',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  const mutated=structuredClone(c);mutated.local_finish_jst='2026-11-09T10:52:00+09:00';
  await assert.rejects(auditOne(mutated,e,w.trust),/candidate_digest_mismatch/);
  const changed=structuredClone(c);changed.candidates.baseline[0]='6-5-4';
  await assert.rejects(auditOne(changed,e,w.trust));
});
test('tampering signed statement field after signature is rejected',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  e.statement.immutable_receipt_id='later-receipt-id';
  await assert.rejects(auditOne(c,e,w.trust),/signed_witness_attestation_invalid/);
});
test('wrong key and wrong independent pin both fail',async()=>{
  const c=candidate(),w=witness(),other=witness(),e=envelope(c,w);
  await assert.rejects(auditOne(c,e,other.trust),/key_fingerprint_not_pinned|signed_witness_attestation_invalid/);
  await assert.rejects(auditOne(c,e,{...w.trust,spki_sha256:'0'.repeat(64)}),/key_fingerprint_not_pinned/);
});
test('self-declared witness identity never overrides configured trust identity',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  await assert.rejects(auditOne(c,e,{...w.trust,witness_id:'different-recipient'}),/identity_or_candidate/);
  await assert.rejects(auditOne(c,e,{...w.trust,key_id:'different-key'}),/identity_or_candidate/);
});
test('signature format and foreign signature are rejected',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  await assert.rejects(auditOne(c,{...e,signature_b64:'anything'},w.trust),/noncanonical_ed25519_signature/);
  const foreign=witness();
  await assert.rejects(auditOne(c,{...e,signature_b64:envelope(c,foreign).signature_b64},w.trust),/signed_witness_attestation_invalid/);
});
test('extra signed flags, injected outcome and unknown top-level fields fail closed',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  await assert.rejects(auditOne(c,{...e,formal:true},w.trust),/envelope_fields/);
  await assert.rejects(auditOne(c,{...e,statement:{...e.statement,independent_receipt_verified:true}},w.trust),/envelope_fields/);
  const marked=structuredClone(c);marked.confirmed_winner='1-2-3';
  await assert.rejects(auditOne(marked,e,w.trust));
});
test('claimed first-write flag and candidate cutoff cannot be rewritten even if re-signed',async()=>{
  const c=candidate(),w=witness();
  for(const changes of [{claimed_first_write:false},{declared_cutoff_utc:'2026-11-09T03:00:00.000Z'},
    {race_code:'202611090102'},{candidate_record_sha256:'0'.repeat(64)}]){
    await assert.rejects(auditOne(c,envelope(c,w,changes),w.trust),/identity_or_candidate/);
  }
});
test('signed claim at local finish or too near cutoff is still rejected',async()=>{
  const c=candidate(),w=witness();
  for(const stamp of ['2026-11-09T01:51:00.000Z','2026-11-09T01:51:01.000Z',
    '2026-11-09T01:59:58.000Z','2026-11-09T02:00:00.000Z']){
    await assert.rejects(auditOne(c,envelope(c,w,{first_accepted_at_utc_claim:stamp}),w.trust),
      /clock_claim_too_early_late_or_ambiguous/,stamp);
  }
});
test('noncanonical or invalid claimed receipt timestamps fail closed',async()=>{
  const c=candidate(),w=witness();
  for(const stamp of ['2026-11-09T01:55:00Z','2026-11-09T10:55:00+09:00',
    '2026-02-30T01:55:00.000Z','NaN','2026-11-09T01:55:00.000+00:00']){
    await assert.rejects(auditOne(c,envelope(c,w,{first_accepted_at_utc_claim:stamp}),w.trust),
      /untrusted_utc_receipt_clock/,stamp);
  }
});
test('batch with repeated identical witness claim is nonformal and one distinct race',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  const r=await auditBatch([c],{[c.race_code]:[e,e]},w.trust);
  assert.equal(r.examined,1);assert.equal(r.signed_claim_races,1);
  assert.equal(r.rows[0].signed_claims_examined,2);
  assert.equal(r.formally_eligible,0);
});
test('same-race conflicting signed immutable receipt IDs quarantined',async()=>{
  const c=candidate(),w=witness(),a=envelope(c,w),b=envelope(c,w,{immutable_receipt_id:'different-id'});
  const r=await auditBatch([c],{[c.race_code]:[a,b]},w.trust);
  assert.equal(r.quarantined_signed_claim_conflicts,1);
  assert.equal(r.rows[0].status,'signed_first_receipt_conflict_quarantined');
  assert.equal(r.formally_eligible,0);
});
test('same-race two signed first timestamps also quarantined',async()=>{
  const c=candidate(),w=witness(),a=envelope(c,w),b=envelope(c,w,{first_accepted_at_utc_claim:'2026-11-09T01:56:00.000Z'});
  const r=await auditBatch([c],{[c.race_code]:[a,b]},w.trust);
  assert.equal(r.quarantined_signed_claim_conflicts,1);
});
test('missing witness does not skip candidate schema validation or grant eligibility',async()=>{
  const c=candidate(),w=witness(),r=await auditBatch([c],{},w.trust);
  assert.equal(r.missing_signed_claim_races,1);assert.equal(r.formally_eligible,0);
  const invalid={...c,formal:true};
  await assert.rejects(auditBatch([invalid],{},w.trust));
});
test('duplicate race and orphan witness rejected without second denominator',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  await assert.rejects(auditBatch([c,c],{[c.race_code]:[e]},w.trust),/duplicate_or_invalid_frozen_race/);
  await assert.rejects(auditBatch([c],{'202611090102':[e]},w.trust),/orphan_witness_attestation/);
});
test('invalid trust anchor rejected; never generate/persist verifier signing secrets',async()=>{
  const c=candidate(),w=witness(),e=envelope(c,w);
  for(const tr of [null,{}, {...w.trust,unexpected_formal:true},
                   {...w.trust,public_key_pem:'not a key'},
                   {...w.trust,spki_sha256:'not-a-hash'}]){
    await assert.rejects(auditOne(c,e,tr));
  }
});


// Cross-race and cross-run negative evidence: all data below are synthetic.
test('two valid signatures with same receipt ID for DIFFERENT race codes are quarantined',async()=>{
  const w=witness(),a=candidate(),b=candidate('202611090102');
  const r=await auditBatch([a,b],{
    [a.race_code]:[envelope(a,w)],
    [b.race_code]:[envelope(b,w)],
  },w.trust);
  assert.equal(r.examined,2);
  assert.equal(r.race_ids_quarantined_for_cross_race_receipt_id,2);
  assert.equal(r.quarantined_signed_claim_conflicts,2);
  assert.ok(r.rows.every(x=>x.cross_race_receipt_id_collision===true));
  assert.equal(r.formally_eligible,0);
});
test('different immutable receipt IDs across different races are not falsely quarantined',async()=>{
  const w=witness(),a=candidate(),b=candidate('202611090102');
  const r=await auditBatch([a,b],{
    [a.race_code]:[envelope(a,w)],
    [b.race_code]:[envelope(b,w,{immutable_receipt_id:'receipt-for-race-b'})],
  },w.trust);
  assert.equal(r.race_ids_quarantined_for_cross_race_receipt_id,0);
  assert.equal(r.signed_claim_races,2);
  assert.equal(r.formally_eligible,0);
});
test('cross-batch repeat of same candidate + same signed receipt does not count twice',async()=>{
  const w=witness(),c=candidate(),e=envelope(c,w);
  const batch={records:[c],envelopes:{[c.race_code]:[e]}};
  const r=await auditAcrossBatches([batch,structuredClone(batch)],w.trust);
  assert.equal(r.batches_examined,2);
  assert.equal(r.candidate_observations,2);
  assert.equal(r.distinct_race_codes,1);
  assert.equal(r.repeated_same_candidate_observations_not_counted_again,1);
  assert.equal(r.race_ids_quarantined_for_conflicts,0);
  assert.equal(r.formally_eligible,0);
});
test('cross-batch changed same-race candidate digest triggers quarantine',async()=>{
  const w=witness(),a=candidate(),b=structuredClone(a);
  b.local_finish_jst='2026-11-09T10:52:00+09:00';
  const r=await auditAcrossBatches([
    {records:[a],envelopes:{[a.race_code]:[envelope(a,w)]}},
    {records:[b],envelopes:{[b.race_code]:[envelope(b,w)]}},
  ],w.trust);
  assert.equal(r.distinct_race_codes,1);
  assert.equal(r.race_ids_quarantined_for_conflicts,1);
  assert.equal(r.rows[0].repeated_candidate_with_changed_bytes,true);
  assert.equal(r.rows[0].status,'cross_batch_candidate_or_signed_receipt_conflict_quarantined');
});
test('cross-batch same-race signed first acceptance timestamp conflict is quarantined',async()=>{
  const w=witness(),c=candidate();
  const r=await auditAcrossBatches([
    {records:[c],envelopes:{[c.race_code]:[envelope(c,w)]}},
    {records:[c],envelopes:{[c.race_code]:[envelope(c,w,{
      first_accepted_at_utc_claim:'2026-11-09T01:56:00.000Z',
    })]}},
  ],w.trust);
  assert.equal(r.rows[0].distinct_claimed_first_acceptance_clocks,2);
  assert.equal(r.rows[0].conflicting_signed_first_write_claims,true);
  assert.equal(r.race_ids_quarantined_for_conflicts,1);
});
test('cross-batch different receipt IDs for the same candidate are quarantined',async()=>{
  const w=witness(),c=candidate();
  const r=await auditAcrossBatches([
    {records:[c],envelopes:{[c.race_code]:[envelope(c,w)]}},
    {records:[c],envelopes:{[c.race_code]:[envelope(c,w,{
      immutable_receipt_id:'some-new-first-id',
    })]}},
  ],w.trust);
  assert.equal(r.rows[0].distinct_claimed_immutable_receipt_ids,2);
  assert.equal(r.race_ids_quarantined_for_conflicts,1);
});
test('cross-batch recycled receipt ID across separate race codes quarantines both',async()=>{
  const w=witness(),a=candidate(),b=candidate('202611090102');
  const r=await auditAcrossBatches([
    {records:[a],envelopes:{[a.race_code]:[envelope(a,w)]}},
    {records:[b],envelopes:{[b.race_code]:[envelope(b,w)]}},
  ],w.trust);
  assert.equal(r.race_ids_with_cross_race_receipt_id_reuse,2);
  assert.equal(r.race_ids_quarantined_for_conflicts,2);
  assert.ok(r.rows.every(x=>x.cross_race_receipt_id_reuse));
});
test('cross-batch valid separate races stay separate, though still nonformal',async()=>{
  const w=witness(),a=candidate(),b=candidate('202611090102');
  const r=await auditAcrossBatches([
    {records:[a],envelopes:{[a.race_code]:[envelope(a,w)]}},
    {records:[b],envelopes:{[b.race_code]:[envelope(b,w,{
      immutable_receipt_id:'unique-for-race-b',
    })]}},
  ],w.trust);
  assert.equal(r.distinct_race_codes,2);
  assert.equal(r.race_ids_quarantined_for_conflicts,0);
  assert.equal(r.formally_eligible,0);
  assert.equal(r.independent_first_receipt_verified,0);
  assert.equal(r.independent_witness_key_custody_verified,false);
});
test('same race with missing and later signed claim is still not independently proven',async()=>{
  const w=witness(),c=candidate();
  const r=await auditAcrossBatches([
    {records:[c],envelopes:{}},
    {records:[c],envelopes:{[c.race_code]:[envelope(c,w)]}},
  ],w.trust);
  assert.equal(r.rows[0].verified_under_supplied_key_claims,1);
  assert.equal(r.rows[0].candidate_observations,2);
  assert.equal(r.race_ids_quarantined_for_conflicts,0);
  assert.equal(r.formally_eligible,0);
});
test('cross-batch forged schema, malformed receipt or orphan fails closed',async()=>{
  const w=witness(),c=candidate();
  for(const batch of [
    {records:[c],envelopes:{},formal:true},
    {records:[c],envelopes:{'202611090102':[envelope(c,w)]}},
    {records:[{...c,formal:true}],envelopes:{}},
    {records:[c],envelopes:{[c.race_code]:[{
      ...envelope(c,w),signature_b64:'invalid'
    }]}},
  ]){
    await assert.rejects(auditAcrossBatches([batch],w.trust));
  }
});
test('cross-batch empty or too many unverified runs rejected without scoring',async()=>{
  const w=witness();
  await assert.rejects(auditAcrossBatches([],w.trust),/untrusted_cross_batch_receipt_roster/);
  await assert.rejects(auditAcrossBatches(Array.from({length:41},()=>({
    records:[],envelopes:{}
  })),w.trust),/untrusted_cross_batch_receipt_roster/);
});
