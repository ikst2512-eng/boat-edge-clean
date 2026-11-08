/** Offline mock D1 and HTTP unit tests; never deploys or accesses network. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {handle, validateRecord, canonicalRecord, INSERT_SQL, SELECT_SQL} from './hole_pair_first_receipt_worker.mjs';

const TOKEN='research-test-token-exactly-64-characters-long-0123456789abcdef';
const SHA='ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb';
const BLOBS={
  'hole_third_choice_research.py':'579edc1ae846489d447307fbf03b35fc7d4c09b9',
  'hole_pair_diversification_research.py':'56f06c10f6d07e03b2e37624ecf57dc6de7d8748',
  'hole_top5_safe_bundle_research.py':'a43f53d898ac73829e7f2b24f81624d69d26d74a',
  'hole_pair_third_bundle_research.py':'88c4ed506588a24bb593d104b5d0f59c7502d73a'
};
const PICKS=['1-2-3','1-2-4','1-3-2','1-3-4','2-1-3','2-1-4','1-4-2','1-4-3','2-3-1','2-3-4'];
const digest=x=>createHash('sha256').update(x).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':
  x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
function candidate(){
  const choices={baseline:[...PICKS],same_pair_two_thirds:[...PICKS],two_pairs_one_third:[...PICKS]};
  return {
    schema:'HOLE_PAIR_FUTURE_FREEZE_V1',status:'locally_frozen_unverified',race_code:'202611090101',
    method:'HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1',method_source_sha256:SHA,
    model_version:'CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED',
    source_sha256:'a'.repeat(64),source_git_blob_sha1:'b'.repeat(40),
    locked_selector_git_blobs:{...BLOBS},candidates:choices,candidates_sha256:digest(canonical(choices)),
    local_start_jst:'2026-11-09T10:50:00+09:00',local_finish_jst:'2026-11-09T10:51:00+09:00',
    t_minus_12_jst:'2026-11-09T11:00:00+09:00',deadline_jst:'2026-11-09T11:12:00+09:00',
    formal:false,prospective_validation:false,independent_first_receipt_verified:false,
    production_forecast_changed:false
  };
}
class DBMock {
  constructor(clock='2026-11-09T01:55:00.000Z'){this.clock=clock;this.rows=new Map();this.attempts=0;}
  prepare(sql){
    assert.ok(sql===INSERT_SQL||sql===SELECT_SQL,'unexpected SQL');
    return {bind:(...params)=>({first:async()=>{
      if(sql===SELECT_SQL)return this.rows.get(params[0])||null;
      ++this.attempts;
      const [code,hash,bytes,cutoff,cutoffCondition,finish]=params;
      assert.equal(cutoff,cutoffCondition);
      const now=Math.floor(Date.parse(this.clock)/1000);
      if(!this.rows.has(code) && now+2<Math.floor(Date.parse(cutoff)/1000) &&
         now>Math.floor(Date.parse(finish)/1000)){
        const row={race_code:code,candidate_sha256:hash,canonical_record:bytes,
          cutoff_utc:cutoff,first_received_at_utc:this.clock};
        this.rows.set(code,row);return row;
      }
      return null;
    }})};
  }
}
function request(r=candidate(),{token=TOKEN,type='application/json',path='/v1/first-accept',method='POST'}={}){
  return new Request('https://receiver.example'+path,{method,
    headers:{Authorization:'Bearer '+token,'Content-Type':type},
    ...(method==='POST'?{body:JSON.stringify({record:r})}:{})});
}
async function post(db,r=candidate(),options={}){
  const response=await handle(request(r,options),{DB:db,RECEIPT_TOKEN:TOKEN});
  return {status:response.status,data:await response.json()};
}

test('canonical record hash and JST deadline are reproducible',async()=>{
  const r=candidate(), v=await validateRecord(r);
  assert.equal(v.code,r.race_code);
  assert.equal(v.cutoff_utc,'2026-11-09T02:00:00.000Z');
  assert.equal(v.finish_utc,'2026-11-09T01:51:00.000Z');
  assert.equal(digest(v.record_text),digest(canonicalRecord(r)));
});
test('first acceptance is database timestamp, not caller timestamp',async()=>{
  const db=new DBMock(),a=await post(db);
  assert.equal(a.status,200);assert.equal(a.data.first_received_at_utc,db.clock);
  assert.equal(a.data.already_recorded,false);assert.equal(db.rows.size,1);
  for(const key of ['formal','production_promotion_allowed','independent_first_receipt_verified','official_t12_complete_verified'])assert.equal(a.data[key],false);
});
test('retry preserves first timestamp even when retry is late',async()=>{
  const db=new DBMock();await post(db);db.clock='2026-11-09T03:10:00.000Z';
  const a=await post(db);assert.equal(a.status,200);assert.equal(a.data.already_recorded,true);
  assert.equal(a.data.first_received_at_utc,'2026-11-09T01:55:00.000Z');
});
test('corrupted persisted first-receipt clocks never pass on identical retry',async()=>{
  const invalid=[
    '2026-11-09T01:50:59.999Z', // before the frozen candidate finish
    '2026-11-09T01:51:00.000Z', // same time as finish
    '2026-11-09T01:59:58.000Z', // exactly two seconds before cutoff
    '2026-11-09T01:59:59.000Z',
    '2026-11-09T02:00:00.000Z',
    '2026-11-09T02:05:00.000Z',
    '2026-11-09T01:55:00Z',     // D1 schema emits fixed milliseconds
    '2026-11-09T01:55:00+09:00',
    'not-a-clock',
  ];
  for(const clock of invalid){
    const db=new DBMock();
    assert.equal((await post(db)).status,200);
    db.rows.get('202611090101').first_received_at_utc=clock;
    const a=await post(db);
    assert.equal(a.status,409,clock);
    assert.equal(a.data.status,'stored_first_acceptance_clock_untrusted',clock);
    assert.equal(db.rows.size,1,clock);
    assert.equal(db.rows.get('202611090101').first_received_at_utc,clock);
  }
});
test('valid persisted D1 timestamp still never promotes formal proof',async()=>{
  const db=new DBMock();
  assert.equal((await post(db)).status,200);
  db.rows.get('202611090101').first_received_at_utc='2026-11-09T01:59:57.000Z';
  db.clock='2026-11-09T02:10:00.000Z'; // retry well after cutoff
  const a=await post(db);
  assert.equal(a.status,200);
  assert.equal(a.data.already_recorded,true);
  assert.equal(a.data.independent_first_receipt_verified,false);
  assert.equal(a.data.official_t12_complete_verified,false);
  assert.equal(a.data.formal,false);
  assert.equal(a.data.production_promotion_allowed,false);
});
test('same race changed bytes are rejected without overwriting',async()=>{
  const db=new DBMock();await post(db);const r=candidate();r.local_finish_jst='2026-11-09T10:52:00+09:00';
  const a=await post(db,r);assert.equal(a.status,409);assert.equal(a.data.status,'conflicting_first_acceptance');
  assert.equal(db.rows.size,1);
});
test('late new submissions are never accepted',async()=>{
  const db=new DBMock('2026-11-09T02:01:00.000Z'),a=await post(db);
  assert.equal(a.status,409);assert.equal(db.rows.size,0);
});
test('two-second cutoff boundary rejects same-second ambiguity',async()=>{
  for(const now of ['2026-11-09T01:59:58.000Z','2026-11-09T01:59:59.000Z','2026-11-09T02:00:00.000Z']){
    const db=new DBMock(now),a=await post(db);assert.equal(a.status,409);assert.equal(db.rows.size,0);
  }
});
test('server cannot receive prior to claimed candidate finish',async()=>{
  const db=new DBMock('2026-11-09T01:50:00.000Z');
  assert.equal((await post(db)).status,409);assert.equal(db.rows.size,0);
});
test('simultaneous conflicting submissions preserve one first record',async()=>{
  const db=new DBMock();const r=candidate();r.local_finish_jst='2026-11-09T10:52:00+09:00';
  const [a,b]=await Promise.all([post(db,candidate()),post(db,r)]);
  assert.equal(db.rows.size,1);assert.deepEqual([a.status,b.status].sort(),[200,409]);
});
test('authentication required, including for retries',async()=>{
  const db=new DBMock();
  assert.equal((await post(db,candidate(),{token:'wrong'})).status,401);
  assert.equal((await post(db)).status,200);
  assert.equal((await post(db,candidate(),{token:'wrong'})).status,401);
});
test('no DB and no secret both fail closed',async()=>{
  assert.equal((await handle(request(),{RECEIPT_TOKEN:TOKEN})).status,503);
  assert.equal((await handle(request(),{DB:new DBMock()})).status,401);
});
test('invalid HTTP routes, methods and content-type refused',async()=>{
  const db=new DBMock();
  assert.equal((await post(db,candidate(),{type:'text/plain'})).status,415);
  assert.equal((await post(db,candidate(),{path:'/v1/other'})).status,404);
  assert.equal((await post(db,candidate(),{method:'GET'})).status,404);
  assert.equal(db.rows.size,0);
});
test('false hashes, changed selectors, protected Top5 and formal assertions fail',async()=>{
  const db=new DBMock();let r=candidate();r.method_source_sha256='0'.repeat(64);
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.locked_selector_git_blobs['hole_third_choice_research.py']='0'.repeat(40);
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.candidates.baseline[0]='6-5-4';
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.candidates.same_pair_two_thirds[0]='6-5-4';
  r.candidates_sha256=digest(canonical(r.candidates));
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.formal=true;assert.equal((await post(db,r)).status,422);
  assert.equal(db.rows.size,0);
});
test('unknown or outcome-bearing candidate fields are rejected before D1 write',async()=>{
  const keys=[
    ['winning_ticket','1-2-3'],
    ['confirmed_result',{trifecta:'1-2-3'}],
    ['result_checked_at','2026-11-09T12:00:00+09:00'],
    ['unreviewed_metadata','post-result'],
  ];
  for(const [key,value] of keys){
    const db=new DBMock(),r=candidate();
    r[key]=value;
    const a=await post(db,r);
    assert.equal(a.status,422,key);
    assert.equal(db.rows.size,0,key);
    assert.equal(db.attempts,0,key);
  }
});
test('candidate freeze source warning cannot smuggle post-result content',async()=>{
  const db=new DBMock(),r=candidate();
  r.warning='Winner was 1-2-3';
  assert.equal((await post(db,r)).status,422);
  assert.equal(db.attempts,0);
});
test('the exact result-blind freeze warning stays compatible',async()=>{
  const db=new DBMock(),r=candidate();
  r.warning='Candidate frozen by a local clock only. No independently verified first receipt; cannot report formal accuracy.';
  const a=await post(db,r);
  assert.equal(a.status,200);
  assert.equal(db.rows.size,1);
  assert.equal(a.data.formal,false);
  assert.equal(a.data.independent_first_receipt_verified,false);
});
test('invalid dates, cutoffs and past cohort rejected',async()=>{
  const db=new DBMock();let r=candidate();r.deadline_jst='2026-11-10T11:12:00+09:00';
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.t_minus_12_jst='2026-11-10T11:00:00+09:00';
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.race_code='202611080101';
  assert.equal((await post(db,r)).status,422);
  r=candidate();r.local_finish_jst='2026-11-09T10:51:00Z';
  assert.equal((await post(db,r)).status,422);
});
test('D1 outage returns no fabricated receipt',async()=>{
  const db={prepare(){throw Error('backend unavailable');}};
  const a=await post(db);assert.equal(a.status,503);assert.equal(a.data.status,'database_unavailable_no_proof');
});
test('oversized upload rejected without touching DB',async()=>{
  const db=new DBMock();
  const r=candidate();r.warning='X'.repeat(41000);
  const a=await post(db,r);assert.equal(a.status,413);assert.equal(db.attempts,0);
});
