/* Read-only bridge from CLEAN racecard-v5 to research entry evidence.
 * CLEAN BoatraceCSV previews are NOT certified official beforeinfo. Never
 * upgrade source labels, invent course-specific records, or edit forecasts.
 */
'use strict';
const {assessEntryEvidence}=require('./entry_evidence_gate.js');
function stNumber(v){
  if(typeof v==='number')return Number.isFinite(v)&&v>=-0.2&&v<=0.5?v:null;
  if(typeof v!=='string'||!/^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(v.trim()))return null;
  const n=Number(v.trim());return n>=-0.2&&n<=0.5?n:null;
}
function sixPermutation(v){return Array.isArray(v)&&v.length===6&&v.every(n=>Number.isInteger(n)&&n>=1&&n<=6)&&new Set(v).size===6;}
function validIso(v){return typeof v==='string'&&/^(?:\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));}
function cleanRacecardEvidence(card,{selectedEntry,courseRecords,officialReceipt}={}){
  const meta=card?.meta||{}, audit=card?.source_audit?.beforeinfo||{};
  const racers=card?.racers, preview=card?.beforeinfo;
  const missing=[];
  const hasSix=Array.isArray(racers)&&racers.length===6&&sixPermutation(racers.map(x=>x?.lane));
  if(!hasSix)missing.push('racecard_six_racers_unverified');
  const stt=preview?.start_exhibition;
  const sttValid=Array.isArray(stt)&&stt.length===6&&sixPermutation(stt.map(x=>x?.lane))&&
    sixPermutation(stt.map(x=>x?.course))&&stt.every(x=>stNumber(x.st)!==null);
  const sourceStt=audit.sources?.stt,sourceTkz=audit.sources?.tkz;
  const cutoffAt=/^\d{4}-\d\d-\d\d$/.test(meta.date||'')&&/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(meta.deadline||'')
    ?meta.date+'T'+meta.deadline+':00+09:00':null;
  const cutoff=Date.parse(cutoffAt);
  if(!Number.isFinite(cutoff))missing.push('racecard_deadline_missing');
  // Both preview receipts must be independently valid and before cutoff.
  for(const [name,receipt] of [['stt',sourceStt],['tkz',sourceTkz]]){
    if(!validIso(receipt?.observed_at)||!Number.isFinite(cutoff)||Date.parse(receipt.observed_at)>=cutoff)
      missing.push(name+'_receipt_not_proven_before_deadline');
    if(!/^[a-f0-9]{64}$/.test(receipt?.sha256||''))missing.push(name+'_raw_hash_missing');
  }
  if(audit.status!=='ok'||!sttValid)missing.push('six_entry_and_exhibition_st_unverified');
  const officialEntry=sttValid?stt.slice().sort((a,b)=>a.course-b.course).map(x=>x.lane):null;
  const entry=selectedEntry===undefined?(officialEntry||[1,2,3,4,5,6]):selectedEntry;
  // The current card's source is a third-party snapshot, not BOAT RACE official.
  const certified=officialReceipt?.verified===true&&officialReceipt?.source==='official_beforeinfo'&&
    validIso(officialReceipt?.observedAt)&&Number.isFinite(cutoff)&&Date.parse(officialReceipt.observedAt)<cutoff&&
    sixPermutation(officialReceipt?.entry)&&
    sixPermutation(officialEntry)&&officialEntry.every((n,i)=>n===officialReceipt.entry[i]);
  const records=Array.isArray(courseRecords)?courseRecords.map(r=>({...r})):[];
  const byBoat=Array.isArray(stt)?new Map(stt.map(x=>[x.lane,x])):new Map();
  // The original snapshot provides exhibition ST, not course-specific stats.
  // Do not label preview ST as official unless a separate official receipt exists.
  if(!certified)missing.push('official_beforeinfo_receipt_missing');
  if(!Array.isArray(courseRecords)||courseRecords.length!==6)missing.push('course_specific_six_boat_dataset_missing');
  const mapped=records.map(row=>{
    const raw=byBoat.get(row.boat);
    return {...row,exhibitionST:certified?stNumber(raw?.st):null,
      exhibitionSource:certified?'official_beforeinfo':'unverified_preview',
      observedAt:row.observedAt||null};
  });
  const evidence={entry,officialEntry:certified?officialEntry:null,
    entrySource:certified?'official_beforeinfo':'third_party_preview',
    entryObservedAt:certified?officialReceipt.observedAt:null,
    cutoffAt,boats:mapped};
  const gate=assessEntryEvidence(evidence);
  return {raceKey:card?.race_key||null,schema:'entry-racecard-evidence-v1',
    observedEntry:officialEntry,selectedEntry:entry,
    source:'CLEAN racecard-v5 / BoatraceCSV preview (uncertified)',
    previewST:sttValid?stt.map(x=>({boat:x.lane,course:x.course,st:stNumber(x.st)})):[],
    missing:[...new Set([...missing,...gate.failures])],
    evidenceComplete:missing.length===0&&gate.evidenceComplete,
    formalForecastApproved:false,confidenceCalibrated:false,
    existingForecastsUnchanged:true};
}
module.exports={cleanRacecardEvidence,stNumber};
