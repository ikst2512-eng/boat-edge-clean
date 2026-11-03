const assert=require('node:assert/strict');
const {test}=require('node:test');
const {cleanRacecardEvidence,stNumber}=require('../entry_racecard_evidence.js');
function fixture(){
 const at='2026-11-03T19:00:00+09:00',hash='a'.repeat(64);
 return {schema_version:'boat-edge-race-v5',race_key:'20261103-07-08',
 meta:{date:'2026-11-03',deadline:'19:20',phase:'PRE_RESULT',results_seen:false},
 racers:[1,2,3,4,5,6].map(lane=>({lane,registration_no:String(4000+lane),national:{win_rate:5}})),
 source_audit:{beforeinfo:{status:'ok',source:'BoatraceCSV predeadline snapshots',
 sources:{stt:{observed_at:at,sha256:hash},tkz:{observed_at:at,sha256:hash}}}},
 beforeinfo:{start_exhibition:[1,2,3,4,5,6].map(lane=>({lane,course:lane,st:'.12'}))}};
}
test('maps actual CLEAN racecard shape to an observed order without inventing course statistics',()=>{
 const x=cleanRacecardEvidence(fixture());
 assert.deepEqual(x.observedEntry,[1,2,3,4,5,6]);
 assert.deepEqual(x.selectedEntry,[1,2,3,4,5,6]);
 assert.equal(x.previewST.length,6);
 assert.equal(x.previewST[0].st,0.12);
 assert.equal(x.evidenceComplete,false);
 assert.equal(x.formalForecastApproved,false);
 assert(x.missing.includes('official_beforeinfo_receipt_missing'));
 assert(x.missing.includes('course_specific_six_boat_dataset_missing'));
 assert.equal(x.existingForecastsUnchanged,true);
});
test('actual swapped courses convert boat-to-course order, never lane number',()=>{
 const f=fixture();f.beforeinfo.start_exhibition[0].course=2;f.beforeinfo.start_exhibition[1].course=1;
 assert.deepEqual(cleanRacecardEvidence(f).observedEntry,[2,1,3,4,5,6]);
});
test('manual permutation cannot acquire official source provenance',()=>{
 const result=cleanRacecardEvidence(fixture(),{selectedEntry:[2,1,3,4,5,6]});
 assert.deepEqual(result.selectedEntry,[2,1,3,4,5,6]);
 assert(result.missing.includes('entry_not_verified_official'));
});
test('caller supplied official proof is ignored rather than upgrading third-party previews',()=>{
 const f=fixture();
 const result=cleanRacecardEvidence(f,{officialReceipt:{verified:true,source:'official_beforeinfo',entry:[1,2,3,4,5,6],observedAt:'2026-11-03T19:00:00+09:00'}});
 assert.equal(result.evidenceComplete,false);
 assert(result.missing.includes('official_beforeinfo_receipt_missing'));
});
test('complete-looking course rows cannot certify unofficial exhibition ST',()=>{
 const records=[1,2,3,4,5,6].map(boat=>({boat,course:boat,courseStarts:100,
 courseWinRate:.2,courseTop2Rate:.4,courseTop3Rate:.6,courseAverageST:.15,
 courseDataSource:'verified_pre_race',observedAt:'2026-11-03T19:00:00+09:00'}));
 const a=cleanRacecardEvidence(fixture(),{courseRecords:records});
 assert.equal(a.evidenceComplete,false);
 assert(a.missing.includes('official_beforeinfo_receipt_missing'));
 assert(a.missing.includes('boat_1_exhibition_source_missing'));
});
test('missing/stale preview receipt and F ST fail closed',()=>{
 const f=fixture();f.source_audit.beforeinfo.sources.stt.observed_at='2026-11-03T19:20:00+09:00';
 f.beforeinfo.start_exhibition[0].st='F.01';
 const a=cleanRacecardEvidence(f);
 assert.equal(a.observedEntry,null);
 assert(a.missing.includes('stt_receipt_not_proven_before_deadline'));
 assert(a.missing.includes('six_entry_and_exhibition_st_unverified'));
});
test('bad card never fabricates observed entry or official evidence',()=>{
 const a=cleanRacecardEvidence(null);
 assert.equal(a.observedEntry,null);assert.equal(a.evidenceComplete,false);
});
test('ST parser retains valid decimals and rejects F or extreme input',()=>{
 assert.equal(stNumber('.14'),.14);assert.equal(stNumber('F.03'),null);
 assert.equal(stNumber('999'),null);assert.equal(stNumber(null),null);
});
