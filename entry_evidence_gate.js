/* Entry-order evidence gate: a contract for future model validation, NOT a new forecast.
 * A manual edit is hypothetical and must never inherit official-entry provenance.
 */
'use strict';
const SIX=[1,2,3,4,5,6];
function permutation(v){return Array.isArray(v)&&v.length===6&&v.every(n=>Number.isInteger(n)&&n>=1&&n<=6)&&new Set(v).size===6;}
function finiteRate(n){return typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1;}
function finiteST(n){return typeof n==='number'&&Number.isFinite(n)&&n>=-0.2&&n<=0.5;}
function assessEntryEvidence(input){
  const x=input&&typeof input==='object'?input:{};
  const failures=[];
  const requireField=(ok,code)=>{if(!ok)failures.push(code);};
  requireField(permutation(x.entry),'invalid_entry');
  requireField(permutation(x.officialEntry),'official_entry_missing');
  const official=permutation(x.entry)&&permutation(x.officialEntry)&&x.entry.every((n,i)=>n===x.officialEntry[i]);
  requireField(official,'entry_not_verified_official');
  requireField(x.entrySource==='official_beforeinfo','official_entry_provenance_missing');
  requireField(x.entryObservedAt&&Number.isFinite(Date.parse(x.entryObservedAt)),'entry_timestamp_missing');
  const cutoff=Date.parse(x.cutoffAt);
  requireField(Number.isFinite(cutoff),'cutoff_timestamp_missing');
  const observed=Date.parse(x.entryObservedAt);
  requireField(Number.isFinite(observed)&&Number.isFinite(cutoff)&&observed<=cutoff,'entry_after_cutoff_or_unverifiable');
  // Each boat must carry course-specific evidence FOR ITS ASSIGNED COURSE,
  // rather than reusing its original lane or national win rate.
  const records=x.boats;
  requireField(Array.isArray(records)&&records.length===6,'six_boat_records_missing');
  if(permutation(x.entry)&&Array.isArray(records)&&records.length===6){
    const ids=records.map(r=>r&&r.boat);
    requireField(permutation(ids),'boat_identity_invalid');
    for(let course=1;course<=6;course++){
      const boat=x.entry[course-1],row=records.find(r=>r&&r.boat===boat);
      if(!row){failures.push('boat_'+boat+'_missing');continue;}
      requireField(row.course===course,'boat_'+boat+'_course_mismatch');
      requireField(Number.isInteger(row.courseStarts)&&row.courseStarts>=1,'boat_'+boat+'_course_sample_missing');
      requireField(finiteRate(row.courseWinRate),'boat_'+boat+'_course_win_rate_missing');
      requireField(finiteRate(row.courseTop2Rate),'boat_'+boat+'_course_top2_rate_missing');
      requireField(finiteRate(row.courseTop3Rate),'boat_'+boat+'_course_top3_rate_missing');
      requireField(finiteST(row.courseAverageST),'boat_'+boat+'_course_st_missing');
      requireField(finiteST(row.exhibitionST),'boat_'+boat+'_exhibition_st_missing');
      requireField(row.courseDataSource==='verified_pre_race','boat_'+boat+'_course_source_missing');
      requireField(row.exhibitionSource==='official_beforeinfo','boat_'+boat+'_exhibition_source_missing');
      const time=Date.parse(row.observedAt);
      requireField(Number.isFinite(time)&&Number.isFinite(cutoff)&&time<=cutoff,'boat_'+boat+'_after_cutoff_or_unverifiable');
    }
  }
  // Evidence completeness is NOT accuracy, calibration, or approval to publish.
  return Object.freeze({evidenceComplete:failures.length===0,formalForecastApproved:false,
    confidenceCalibrated:false,mode:'research_evidence_audit',failures:Object.freeze([...new Set(failures)])});
}
module.exports={assessEntryEvidence};
