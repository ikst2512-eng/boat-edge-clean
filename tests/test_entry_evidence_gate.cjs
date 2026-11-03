const {test}=require('node:test');
const assert=require('node:assert/strict');
const {assessEntryEvidence}=require('../entry_evidence_gate.js');
function valid(){
 return {entry:[1,2,3,4,5,6],officialEntry:[1,2,3,4,5,6],
 entrySource:'official_beforeinfo',entryObservedAt:'2026-11-03T19:00:00+09:00',cutoffAt:'2026-11-03T19:10:00+09:00',
 boats:Array.from({length:6},(_,i)=>({boat:i+1,course:i+1,courseStarts:100,
 courseWinRate:0.3,courseTop2Rate:0.5,courseTop3Rate:0.7,courseAverageST:0.14,exhibitionST:0.12,
 courseDataSource:'verified_pre_race',exhibitionSource:'official_beforeinfo',
 observedAt:'2026-11-03T19:00:00+09:00'}))};
}
test('complete evidence is never mistaken for validated formal forecast',()=>{
 const x=assessEntryEvidence(valid());assert.equal(x.evidenceComplete,true);
 assert.equal(x.formalForecastApproved,false);assert.equal(x.confidenceCalibrated,false);
});
test('manual permutation is always hypothetical even with complete original evidence',()=>{
 const x=valid();x.entry=[2,1,3,4,5,6];
 const result=assessEntryEvidence(x);assert.equal(result.evidenceComplete,false);
 assert(result.failures.includes('entry_not_verified_official'));
 assert(result.failures.includes('boat_2_course_mismatch'));
});
test('cutoff is enforced on entry and each boat data receipt',()=>{
 const x=valid();x.entryObservedAt='2026-11-03T19:11:00+09:00';
 x.boats[0].observedAt='2026-11-03T19:12:00+09:00';
 const result=assessEntryEvidence(x);assert(result.failures.includes('entry_after_cutoff_or_unverifiable'));
 assert(result.failures.includes('boat_1_after_cutoff_or_unverifiable'));
});
test('missing or unverified official entry fails closed',()=>{
 for(const source of [null,'assumed_frame','manual']) {
  const x=valid();x.entrySource=source;
  assert(assessEntryEvidence(x).failures.includes('official_entry_provenance_missing'));
 }
 const x=valid();delete x.officialEntry;
 assert(assessEntryEvidence(x).failures.includes('official_entry_missing'));
});
test('missing ST, course win rate and duplicate boat records cannot pass',()=>{
 const x=valid();x.boats[0].exhibitionST=null;x.boats[1].courseWinRate=undefined;x.boats[2].boat=2;
 const a=assessEntryEvidence(x);
 assert.equal(a.evidenceComplete,false);
 for(const code of ['boat_1_exhibition_st_missing','boat_2_course_win_rate_missing','boat_identity_invalid','boat_3_missing'])assert(a.failures.includes(code));
});
test('empty input fails safely',()=>{
 assert.equal(assessEntryEvidence(null).evidenceComplete,false);
});
