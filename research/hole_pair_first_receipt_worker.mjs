/**
 * Draft Cloudflare Worker + D1 first-acceptance transport for hole-pair research.
 * NOT deployed or connected to any job. D1, not Worker/client/GitHub clocks,
 * determines the initial persisted timestamp. Not a formal T-12 attestation.
 */
const METHOD_SHA = "ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb";
const LOCKED_BLOBS = Object.freeze({
  "hole_third_choice_research.py":"579edc1ae846489d447307fbf03b35fc7d4c09b9",
  "hole_pair_diversification_research.py":"56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
  "hole_top5_safe_bundle_research.py":"a43f53d898ac73829e7f2b24f81624d69d26d74a",
  "hole_pair_third_bundle_research.py":"88c4ed506588a24bb593d104b5d0f59c7502d73a"
});
const ARMS = ["baseline", "same_pair_two_thirds", "two_pairs_one_third"];
const HEX64 = /^[0-9a-f]{64}$/;
const HEX40 = /^[0-9a-f]{40}$/;
const JST = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+09:00$/;
const MAX_BYTES = 40000;
// The original result-blind freeze() emits a closed set of candidate fields.
// Reject arbitrary outcome/post-result annotations even when hashes match.
// "warning" is an optional fixed, non-evidence explanatory string.
const REQUIRED_FROZEN_FIELDS = Object.freeze([
  "schema","method","status","race_code","model_version",
  "deadline_jst","t_minus_12_jst","local_start_jst","local_finish_jst",
  "source_sha256","source_git_blob_sha1","locked_selector_git_blobs",
  "method_source_sha256","candidates","candidates_sha256",
  "formal","prospective_validation","independent_first_receipt_verified",
  "production_forecast_changed"
]);
const FROZEN_WARNING = "Candidate frozen by a local clock only. No independently verified first receipt; cannot report formal accuracy.";
function closedFreezeSchema(r){
  const keys=Object.keys(r), allowed=new Set([...REQUIRED_FROZEN_FIELDS,"warning"]);
  return REQUIRED_FROZEN_FIELDS.every(key=>Object.hasOwn(r,key)) &&
    keys.every(key=>allowed.has(key)) &&
    (!Object.hasOwn(r,"warning") || r.warning===FROZEN_WARNING);
}

// The SQLite engine supplies the timestamp and performs the cutoff check
// atomically with INSERT. Never make that decision from Date.now() in JS.
export const INSERT_SQL = [
  "INSERT OR IGNORE INTO hole_pair_first_receipts",
  "(race_code, candidate_sha256, canonical_record, cutoff_utc)",
  "SELECT ?, ?, ?, ?",
  "WHERE CAST(strftime('%s', 'now') AS INTEGER) + 2 < CAST(strftime('%s', ?) AS INTEGER)",
  "AND CAST(strftime('%s', 'now') AS INTEGER) > CAST(strftime('%s', ?) AS INTEGER)",
  "RETURNING race_code, candidate_sha256, cutoff_utc, first_received_at_utc"
].join("\n");
export const SELECT_SQL = [
  "SELECT race_code, candidate_sha256, cutoff_utc, first_received_at_utc,",
  "canonical_record FROM hole_pair_first_receipts WHERE race_code = ?"
].join("\n");

function reject(message) { throw new Error(message); }
function object(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
function hex(bytes) { return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join(''); }
async function sha256(bytes) { return hex(await crypto.subtle.digest('SHA-256', bytes)); }
function canonical(x) {
  if (Array.isArray(x)) return '[' + x.map(canonical).join(',') + ']';
  if (object(x)) return '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canonical(x[k])).join(',') + '}';
  if (typeof x === 'string' || x === null || typeof x === 'boolean' ||
      (typeof x === 'number' && Number.isFinite(x))) return JSON.stringify(x);
  return reject('non_json_canonical_value');
}
export const canonicalRecord = (x) => canonical(x) + '\n';

function readJst(x) {
  if (typeof x !== 'string' || !JST.test(x)) reject('invalid_jst_clock');
  const time = Date.parse(x);
  if (!Number.isFinite(time)) reject('unparseable_clock');
  return time;
}
function validRace(code) {
  if (typeof code !== 'string' || !/^20\d{10}$/.test(code) || code.slice(0, 8) < '20261109') return false;
  const y=Number(code.slice(0,4)),m=Number(code.slice(4,6)),d=Number(code.slice(6,8));
  const date=new Date(Date.UTC(y,m-1,d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth()+1 !== m || date.getUTCDate() !== d) return false;
  return Number(code.slice(8,10)) >= 1 && Number(code.slice(8,10)) <= 24 &&
         Number(code.slice(10,12)) >= 1 && Number(code.slice(10,12)) <= 12;
}
function ticket(t) { return typeof t === 'string' && /^[1-6]-[1-6]-[1-6]$/.test(t) && new Set(t.split('-')).size===3; }
function pair(t) { return t.slice(0, 3); }

export async function validateRecord(r) {
  if (!object(r) || !closedFreezeSchema(r)) reject('candidate_result_blind_schema_violation');
  if (!validRace(r.race_code) || r.schema !== 'HOLE_PAIR_FUTURE_FREEZE_V1' ||
      r.status !== 'locally_frozen_unverified' || r.method !== 'HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1' ||
      r.method_source_sha256 !== METHOD_SHA ||
      r.model_version !== 'CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED') reject('untrusted_candidate_identity_or_method');
  if (r.formal !== false || r.prospective_validation !== false ||
      r.independent_first_receipt_verified !== false || r.production_forecast_changed !== false)
    reject('forged_formal_candidate_claim');
  if (!HEX64.test(r.source_sha256||'') || !HEX40.test(r.source_git_blob_sha1||''))
    reject('untrusted_original_source_digest');
  if (!object(r.locked_selector_git_blobs) ||
      canonical(r.locked_selector_git_blobs) !== canonical(LOCKED_BLOBS)) reject('locked_selector_blob_mismatch');
  if (!object(r.candidates) ||
      canonical(Object.keys(r.candidates).sort()) !== canonical(ARMS.slice().sort())) reject('missing_candidates');
  const digest=await sha256(new TextEncoder().encode(canonical(r.candidates)));
  if (digest !== r.candidates_sha256) reject('candidate_sha256_mismatch');
  const base = r.candidates.baseline;
  if (!Array.isArray(base) || base.length!==10 || new Set(base).size!==10 ||
      !base.every(ticket)) reject('invalid_baseline_ticket_budget');
  const originalPairs=new Set(base.map(pair));
  for(const arm of ARMS){
    const list=r.candidates[arm];
    if(!Array.isArray(list)||list.length!==10||new Set(list).size!==10||!list.every(ticket)||
       canonical(list.slice(0,5))!==canonical(base.slice(0,5)) ||
       !Array.from(originalPairs).every(p=>new Set(list.map(pair)).has(p)))
      reject('protected_top5_or_pair_coverage_failed');
  }
  const start=readJst(r.local_start_jst), finish=readJst(r.local_finish_jst),
        deadline=readJst(r.deadline_jst),cutoff=readJst(r.t_minus_12_jst);
  const day=r.deadline_jst.slice(0,4)+r.deadline_jst.slice(5,7)+r.deadline_jst.slice(8,10);
  if (day!==r.race_code.slice(0,8) || start>finish || finish>=cutoff ||
      deadline-cutoff!==12*60*1000) reject('candidate_clock_or_cutoff_invalid');
  return { code:r.race_code, cutoff_utc:new Date(cutoff).toISOString(),
    finish_utc:new Date(finish).toISOString(), record_text:canonicalRecord(r) };
}
async function authorized(request, env) {
  const stored=env.RECEIPT_TOKEN;
  const supplied=request.headers.get('Authorization');
  if(typeof stored!=='string'||stored.length<32||typeof supplied!=='string'||
     !supplied.startsWith('Bearer ')||supplied.length>200) return false;
  const a=await sha256(new TextEncoder().encode(supplied.slice(7)));
  const b=await sha256(new TextEncoder().encode(stored));
  return a===b;
}
function reply(status, body){return new Response(JSON.stringify(body), {
  status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
});}
// Defense in depth: SELECT on an existing row is not itself proof of a
// compliant first insert. Reject contradictory stored timestamps on retries.
// This cannot establish provider/admin independence or an official cutoff.
function storedFirstClockValid(row, normalized) {
  const clock = row?.first_received_at_utc;
  if (typeof clock !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(clock))
    return false;
  const first = Date.parse(clock);
  const finish = Date.parse(normalized.finish_utc);
  const cutoff = Date.parse(normalized.cutoff_utc);
  return Number.isFinite(first) && new Date(first).toISOString() === clock &&
    Number.isFinite(finish) && Number.isFinite(cutoff) &&
    first > finish && first + 2000 < cutoff;
}
function receiptRow(row, repeated){return {
  schema:'HOLE_PAIR_D1_FIRST_ACCEPTANCE_V1',race_code:row.race_code,
  candidate_sha256:row.candidate_sha256,declared_cutoff_utc:row.cutoff_utc,
  first_received_at_utc:row.first_received_at_utc,already_recorded:repeated,
  timestamp_origin:'D1 SQLite server clock at successful immutable insertion',
  independent_server_acceptance_observed:true,
  independent_first_receipt_verified:false,official_t12_complete_verified:false,
  formal:false,production_promotion_allowed:false,
  warning:'D1 first-insert time is not an independently signed external witness or official deadline certification.'
};}

export async function handle(request, env){
  const url=new URL(request.url);
  if(url.pathname!=='/v1/first-accept'||request.method!=='POST') return reply(404,{status:'not_found'});
  if(!(await authorized(request,env))) return reply(401,{status:'unauthorized'});
  if(!env.DB || typeof env.DB.prepare !== 'function') return reply(503,{status:'receiver_unconfigured'});
  if(!/^application\/json(?:\s*;.*)?$/i.test(request.headers.get('content-type')||'')) return reply(415,{status:'json_required'});
  const declared=Number(request.headers.get('content-length'));
  if(Number.isFinite(declared)&&declared>MAX_BYTES) return reply(413,{status:'candidate_too_large'});
  let raw;
  try {
    const reader=request.body?.getReader();
    if(!reader)return reply(400,{status:'request_body_missing'});
    let len=0;const chunks=[];
    for(;;){const {done,value}=await reader.read();if(done)break;
      len+=value.byteLength;if(len>MAX_BYTES){await reader.cancel();return reply(413,{status:'candidate_too_large'});}chunks.push(value);}
    const bytes=new Uint8Array(len);let i=0;for(const part of chunks){bytes.set(part,i);i+=part.byteLength;}
    raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
  }catch{return reply(400,{status:'request_read_failed'});}
  let input,normalized;
  try{
    input=JSON.parse(raw);
    if(!object(input)||Object.keys(input).length!==1||!object(input.record)) reject('request_body_invalid');
    normalized=await validateRecord(input.record);
  }catch{return reply(422,{status:'candidate_untrusted_or_invalid'});}
  const digest=await sha256(new TextEncoder().encode(normalized.record_text));
  try{
    // Unique race code + server NOW and both time gates in a single SQL INSERT.
    const inserted=await env.DB.prepare(INSERT_SQL).bind(
      normalized.code,digest,normalized.record_text,normalized.cutoff_utc,
      normalized.cutoff_utc,normalized.finish_utc
    ).first();
    const row=await env.DB.prepare(SELECT_SQL).bind(normalized.code).first();
    if(!row) return reply(409,{status:'not_accepted_before_t12'});
    if(row.candidate_sha256!==digest||row.canonical_record!==normalized.record_text||
       row.cutoff_utc!==normalized.cutoff_utc)
      return reply(409,{status:'conflicting_first_acceptance'});
    if(!storedFirstClockValid(row,normalized))
      return reply(409,{status:'stored_first_acceptance_clock_untrusted'});
    return reply(200,receiptRow(row,!inserted));
  }catch{return reply(503,{status:'database_unavailable_no_proof'});}
}
export default {fetch:handle};
